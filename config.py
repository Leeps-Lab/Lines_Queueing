import random
import math
import json
import pandas as pd
from os.path import join

#XXX: DATA PATHS
CONFIG_FOLDER = join('Lines_Queueing', 'configs')
GROUP_CSV = join(CONFIG_FOLDER, 'config_group.csv')
PLAYER_CSV = join(CONFIG_FOLDER, 'config_player.csv')

# DATA FORMAT
# [ all data
#     [ group list
#         { round dict
#             { group settings dict }
#             [ player settings list
#                 { player settings dict }
#             ]
#         }
#     ]
# ]

def load_csvs():
    group_df = pd.read_csv(GROUP_CSV)
    player_df = pd.read_csv(PLAYER_CSV)
    return group_df, player_df

def format_data():
    gdf, pdf = load_csvs()
    data = []
    unique_groups = gdf.group_id.unique()
    for grp in unique_groups:
        grp_df = gdf[gdf.group_id == grp]
        grp_df.set_index('num_period', inplace=True)
        grp_dict = grp_df.T.to_dict()
        grplist = [{'settings': v, 'players': []} for k,v in grp_dict.items()]
        for i, period in enumerate(grplist):
            plr_df = pdf[(pdf.group_id == grp) & (pdf.num_period == i + 1)]
            plr_df = plr_df.drop(['block_id', 'num_period', 'group_id', 'player_id'], axis=1)
            grplist[i]['players'] = [*plr_df.T.to_dict().values()]
        data.append(grplist)
    return data

def shuffle(data):
    for i, group in enumerate(data):
        for j, period in enumerate(group):
            if 'start_pos' not in data[i][j]['players'][0]:
                positions = [n for n in range(1, len(period['players']) + 1)]
                random.shuffle(positions)
                for k, player in enumerate(period['players']):
                    data[i][j]['players'][k]['start_pos'] = positions[k]
            random.shuffle(
                data[i][j]['players']
            )  # shuffle order of players within periods
        # random.shuffle(data[i])  # shuffle order of periods withing groups
    random.shuffle(data)  # shuffle order of groups

    return data


# exports data to models.py
# formats data to make it easier for models.py to parse it
def export_data():
    data = format_data() 
    # error handling & filling defaults

    for i, group in enumerate(data):
        for j, period in enumerate(group):
            if 'settings' not in period:
                raise ValueError('Each period must contain settings dict')

            if 'players' not in period:
                raise ValueError('Each period must contain players dict')

            settings = period['settings']
            players = period['players']

            if 'duration' not in settings:
                raise ValueError('Each period settings must have a duration')

            if 'swap_method' not in settings:
                raise ValueError(
                    'Each period settings must have a swap_method variable'
                )

            # For now, will comment out this swap_method check to allow for testing
            # of the double auction
            """
            if settings['swap_method'] not in ['cut', 'swap', 'bid']:
                raise ValueError('Each period settings swap_method variable \
                    must be either \'bid\', \'swap\' or \'cut\'')
            """

            if 'pay_method' not in settings:
                raise ValueError(
                    'Each period settings must have a pay_method variable')

            if settings['pay_method'] not in ['gain', 'lose']:
                raise ValueError(
                    'Each period settings pay_method variable \
                    must be either \'gain\' or \'lose\''
                )
            if 'pay_rate' not in players[0]:
                raise ValueError('Players must have pay_rates')

            if 'service_time' not in players[0]:
                if 'k' not in players[0]:
                    raise ValueError(
                        ('Players must have k or service time')
                    )

                t = settings['duration']
                for k, player in enumerate(players):
                    data[i][j]['players'][k]['service_time'] = round(t * player['k']) 
            #if 'start_pos' not in players[0]:
            #    for k, _ in enumerate(players):
            #        data[i][j]['players'][k]['start_pos'] = k + 1


    #print('exported data is')
    #print(data[0][0])
    with open('older.json', 'w') as outfile:
        json.dump(data, outfile)

    return shuffle(data)

"""
example data:
data = [[
    {  # Type 1: double, no communication, 8 players
        #
        'settings': {
            'duration': 1800,
            'swap_method': 'token',
            'pay_method': 'gain',
            'discrete': True,
            'messaging': False,
        },
        'players': [
            {'pay_rate': 4, 'endowment': 4, 'c': .4, 'k': 0.25},
            {'pay_rate': 4, 'endowment': 4, 'c': .4, 'k': 0.25},
            {'pay_rate': 4, 'endowment': 4, 'c': .4, 'k': 0.25},
            {'pay_rate': 4, 'endowment': 4, 'c': .4, 'k': 0.25},
        ],
    } for i in range(4)
]]

"""

