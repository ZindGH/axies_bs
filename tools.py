import pandas as pd
import re

def get_team_from_logs(log_name: str = 'logs.log', save_name: str = None):
    """ Create pandas dataframe from logs saved

    :param log_name: name of log file
    :param save_name: name of excel file to save in
    :return: pandas dataframe {date_time, team_rank, axieID_0,.., price}
    """
    log = "2023-02-21 16:16:27,145 :: INFO :: Team_rank:241 :: axie_ids:8694318|10064691|6513527 :: Price: 1400.1"
    df = pd.DataFrame(columns=['date_time', 'team_rank', 'axie_ids', 'price'])
    with open('logs.log') as logs:
        lines = logs.readlines()
        for log in lines:
            pattern_log = {
                'date_time': log[0:19],
                'team_rank': re.search("(?<=Team_rank:)[0-9]+", log),
                'axie_ids': re.findall("(?<=axie_ids:)[0-9]+|(?<=\|)[0-9]+", log),
                'price': re.search("(?<=Price: )[0-9]+.[0-9]+$", log)
            }
            if not any(val is None for val in pattern_log.values()):
                pattern_log['team_rank'] = pattern_log['team_rank'].group(0)
                pattern_log['price'] = pattern_log['price'].group(0)
                df = pd.concat([df, pd.json_normalize(pattern_log, sep='_')])
    df = df.join(pd.DataFrame(df.axie_ids.tolist()).add_prefix('axieID_')).astype({'team_rank': int, 'price': float})
    df = df.drop(columns='axie_ids').sort_values(by=['price', 'team_rank']).reset_index(drop=True)
    if save_name:
        df.to_excel(save_name)
    return df

print(get_team_from_logs(save_name='test.xls'))