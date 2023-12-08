import sqlite3
import csv
import pandas as pd

def export_table_to_csv(database_file, table_name, csv_file):
    # Connect to the SQLite database
    connection = sqlite3.connect(database_file)
    cursor = connection.cursor()

    # Fetch all rows from the table
    cursor.execute(f"SELECT title, song_id FROM {table_name}")
    rows = cursor.fetchall()

    # Get the column names
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [column[1] for column in cursor.fetchall()]

    # Write to CSV file
    with open(csv_file, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        
        # Write the header
        csv_writer.writerow(columns)

        # Write the data
        csv_writer.writerows(rows)

    # Close the database connection
    connection.close()

# Example usage
# db_file = 'hash.db'
# table_name = 'song_info'
# csv_file = 'song_info.csv'

# export_table_to_csv(db_file, table_name, csv_file)


import pickle

def read_text_file_and_save_as_pickle(file_path, pickle_file_path, delimiter=','):
    data_map = {'video1.wav': '204617827963634618598620832172870737597', 'video2.wav': '230476917379706672243986883004546463699', 'video3.wav': '216203162624069072433917535835450442722', 'video4.wav': '119607074739588253020170658780573254053', 'video5.wav': '203339425666388805834015871469041169620', 'video6.wav': '322617889341686722232774632760679710718', 'video7.wav': '174549803362931686713640150853128373049', 'video8.wav': '338713913207941808650966089074708445921', 'video9.wav': '91063706873693704359519761250272792473', 'video10.wav': '266235172920869817878280159997390739040', 'video11.wav': '225735071703979430167349849302035159875', 'video12.wav': '291274616422223874188274200365886524907', 'video13.wav': '289332670372006179714910153599660215028', 'video14.wav': '1106219936907304894402142764902920628', 'video15.wav': '188043061130541040430474241316692611916', 'video16.wav': '314196875657608858644393542929983718498', 'video17.wav': '95262337718440871039072416843046012100', 'video18.wav': '230528959617695278783857823791571257625', 'video19.wav': '201772564696176064541885812772754107549', 'video20.wav': '201155004210120539608960738768438843873'}
    song_info = {}
    for i in data_map.keys():
        song_info[data_map[i]] = i

    hash = pd.read_csv(file_path)
    hash['hash'] = hash['hash'].astype(int)
    hash['offset'] = hash['offset'].astype(int)
    hash['song'] = hash['song'].apply(lambda x: song_info[x])

    hash.to_pickle(pickle_file_path)

    # data_as_dict = {}
    
    # with open(file_path, 'r') as file:
    #     for line in file:
    #         hash, offset, id = line.split(delimiter)
    #         data_as_dict[hash] = (offset, song_info[id[:-1]])

    #Save the data as a pickle file
    # with open(pickle_file_path, 'wb') as pickle_file:
    #     pickle.dump(data_as_dict, pickle_file)

# Example usage
text_file_path = '../index_from_pkl/hash.txt'
pickle_file_path = 'hash.pkl'

# read_text_file_and_save_as_pickle(text_file_path, pickle_file_path)
loaded_df = pd.read_pickle(pickle_file_path)
print(loaded_df)

def load_pickle_file(file_path):
    with open(file_path, 'rb') as pickle_file:
        data = pickle.load(pickle_file)
    return data

def load_csv(csv_file):
    hash = pd.read_csv(csv_file)
    hash['hash'] = hash['hash'].astype(int)
    hash['offset'] = hash['offset'].astype(int)
    return hash
