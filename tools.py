import pandas as pd
import re

def get_team_from_logs(log_name: str = 'logs.log', save_name: str = None):
    """ Create pandas dataframe from logs saved

    :param log_name: name of log file
    :param save_name: name of excel file to save in
    :return: pandas dataframe {date_time, team_rank, axieID_0,.., price}
    """
    df = pd.DataFrame(columns=['date_time', 'team_rank', 'axie_ids', 'price'])
    with open('logs.log') as logs:
        lines = logs.readlines()
        for log in lines:
            pattern_log = {
                'date_time': log[0:19],
                'team_rank': re.search("(?<=Team_rank: )[0-9]+", log),
                'axie_ids': re.findall("(?<=axie_ids: )[0-9]+|(?<=\|)[0-9]+", log),
                'price': re.search("(?<=Price: )[0-9]+.[0-9]+$", log)
            }
            if not any(val is None for val in pattern_log.values()):
                pattern_log['team_rank'] = pattern_log['team_rank'].group(0)
                pattern_log['price'] = pattern_log['price'].group(0)
                df = pd.concat([df, pd.json_normalize(pattern_log, sep='_')])
    df = df.reset_index(drop=True).join(pd.DataFrame(df.axie_ids.tolist()).add_prefix('axieID_'))
    df = df.drop(columns='axie_ids').astype({'team_rank': int, 'price': float}).sort_values(by=['price', 'team_rank'])
    if save_name:
        df.to_excel(save_name)
    return df

def erase_log(filename: str = 'logs_rework.log'):
    open(filename, 'w').close()
if __name__ == '__tools__':
    print(get_team_from_logs(save_name=None))