import sqlite3
from sqlite3 import Error
import numpy as np
from datetime import datetime
import os
import numpy as np


class Backup():
    def __init__(self, database_path):
        self.path = database_path

        with self.create_connection(self.path) as self.conn:
            self.cards = self.get('cards')  # Key: Card ID
            self.categories = self.get('categories')  # Key: Category ID
            self.category_assigns = self.get('categoryassigns')  # Key: Card ID
            self.score_files = self.get_score_files()  # Key: Scorefile name

            # Get timestamp of the backup from file name
            _, fname = os.path.split(database_path)
            timestamp = fname.split('-')[-1].split('.')[0]
            self.timestamp = datetime.strptime(timestamp, '%y%m%d%H%M')

    @staticmethod
    def create_connection(db_file):
        try:
            conn = sqlite3.connect(db_file)
            return conn
        except Error as e:
            print(e)

        return None

    def get(self, table):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM pleco_flash_{}".format(table))

        column_names = [elem[0] for elem in cursor.description]
        # Takes the first column of the table as keys for a dictionary
        return dict([(row[0], Entry(dict(zip(column_names[1:], row[1:])))) for row in cursor.fetchall()])

    def get_score_files(self):
        score_file_defs = self.get('scorefiles')

        score_files = dict()

        for i_score_file, score_file_def in score_file_defs.items():
            score_file = self.get('scores_{}'.format(i_score_file))  # Key: Card ID
            score_files[score_file_def.name] = score_file

        return score_files


class Container(dict):
    def __init__(self, *args, **kwargs):
        super(Container, self).__init__(*args, **kwargs)
        self.__dict__ = self


class Entry(Container):
    def __init__(self, *args, **kwargs):
        super(Entry, self).__init__(*args, **kwargs)


class BackupSummary():
    
    def __init__(self, backups_dir):
        self.score_files = dict()

        backups = get_backups(backups_dir)

        for backup in backups:
            timestamp = backup.timestamp

            for score_file in backup.score_files.keys():
                if score_file not in self.score_files:
                    self.score_files[score_file] = dict()

                for card in backup.score_files[score_file]:
                    if card not in self.score_files[score_file]:
                        self.score_files[score_file][card] = dict({'scores': dict(), 
                                                                   'reviewed': dict(),
                                                                   'category': dict()})

                        if card in backup.cards:
                            self.score_files[score_file][card]['simplified'] = backup.cards[card].hw
                            self.score_files[score_file][card]['traditional'] = backup.cards[card].althw
                            self.score_files[score_file][card]['pinyin'] = backup.cards[card].pron

                    self.score_files[score_file][card]['scores'][timestamp] = backup.score_files[score_file][card].score

                    self.score_files[score_file][card]['reviewed'][timestamp] = backup.score_files[score_file][card].reviewed

                    if card in backup.category_assigns:
                        self.score_files[score_file][card]['category'][timestamp] = backup.categories[backup.category_assigns[card]['cat']]
                    else:
                        self.score_files[score_file][card]['category'][timestamp] = None


def get_backups(backups_dir):
    backups = []
    for root, _, fnames in os.walk(os.path.join(backups_dir)):
        valid_fnames = [fname for fname in fnames if fname.split('.')[-1] == 'pqb']

        for i_fname, fname in enumerate(valid_fnames):
            print('Loading Backup {}/{}'.format(i_fname + 1, len(valid_fnames)))
            backups.append(Backup(os.path.join(root, fname)))

    return backups


class Data():
    
    def __init__(self, score_file, reviewed_only=0):
        self.timestamps = []
        self.card_scores = dict()
        self.char_scores = dict()
        self.reviewed = dict()

        for card in score_file:
            for timestamp in score_file[card]['scores']:
                if timestamp not in self.timestamps:
                    self.timestamps.append(timestamp)
                    self.card_scores[timestamp] = dict()
                    self.char_scores[timestamp] = dict()
                    self.reviewed[timestamp] = 0

                self.card_scores[timestamp][card] = score_file[card]['scores'][timestamp]
                self.reviewed[timestamp] += score_file[card]['reviewed'][timestamp]
                
                # Some cards don't have the headwords included and will therefore not be counted
                if 'simplified' in score_file[card]:
                    for character in score_file[card]['simplified']:
                        if character not in self.char_scores:
                            self.char_scores[timestamp][character] = -1
                        
                        if score_file[card]['scores'][timestamp] > self.char_scores[timestamp][character]:
                            self.char_scores[timestamp][character] = score_file[card]['scores'][timestamp]
                

        self.timestamps = sorted(self.timestamps)

    def max_score(self):
        return max([max(scores.values()) for timestamp, scores in self.card_scores.items()])
