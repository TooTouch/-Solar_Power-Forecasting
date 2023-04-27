import pandas as pd
import os
from glob import glob
import argparse
from typing import List
import warnings
warnings.filterwarnings(action='ignore')



def read_file(file_path: str) -> pd.DataFrame:
    '''
    read file with checking file extension
    '''
    
    try:
        # check file extension name
        if os.path.splitext(file_path)[1] == '.csv':
            df = pd.read_csv(file_path)
            
            # check seperation of csv file
            if len(df.columns) == 1:
                df = pd.read_csv(file_path, sep='\t')
        else:
            df = pd.read_excel(file_path)
            
        return df
    except:
        raise 'file path is not clear'

def fill_missing_target(df: pd.DataFrame) -> pd.DataFrame:
    '''
    add missing target date and values
    '''
    
    # make date range
    all_date = pd.date_range(start=df['Date'].min(), end=df['Date'].max(), freq='H')
    
    # check the number of missing values
    nb_missing = len(all_date) - len(df['Date'].unique())
    
    # add missing date
    df = pd.merge(df, pd.Series(all_date, name='Date'), on='Date', how='outer').sort_values('Date')
    
    # fillna
    # fill NaN using yesterday data if it does not exist, using tomorrow data
    df_filled = df.fillna(method='ffill')
    df_filled = df_filled.fillna(method='bfill')
    
    return df_filled, nb_missing

def make_target(df: pd.DataFrame, target: str, target_day: list = [1, 7]) -> pd.DataFrame:
    '''
    make target by pre-defined target day
    '''
    
    
    # init target
    df_init = df[['Date',target]].set_index('Date')
    
    # make target day
    for d in target_day:
        df_target = df_init.shift(periods=-d, freq='D')
        df_target = df_target.rename(columns={target: target+f'_{d}day'})
        
        df = pd.merge(df, df_target.reset_index(), on='Date', how='left')
        
    # remove NaN
    df = df.dropna()
    
    return df
    

def read_plant_data_and_target(plant_dir: str, target: str, target_day: list = [1, 7]) -> pd.DataFrame:
    '''
    read plant data and make targets
    '''
    selected_cols = ['Plant','Inverter','Date']
    
    # read plant data
    df = pd.DataFrame()
    data_list = glob(os.path.join(plant_dir,'*'))
    data_list.sort()
    for path in data_list:
        df = pd.concat([df, read_file(file_path=path)], axis=0)
        
    # drop duplicates
    df = df.drop_duplicates()
    
    # select columns
    df = df[selected_cols + [target]]
    
    # change Date type into pd.datetime
    df['Date'] = pd.to_datetime(df['Date'])
    
    # sort by Inverter and Date columns
    df = df.sort_values(['Inverter','Date'])
    
    # make targets by value of Inverter column. ex) ['KACO 1','KACO 2']
    df_target = pd.DataFrame()
    nb_missing = 0
    for inverter in df['Inverter'].unique():
        df_i = df[df['Inverter']==inverter]
        
        # add missing target
        df_i, nb_missing_i = fill_missing_target(df=df_i)
        nb_missing += nb_missing_i
        
        # make targets
        df_i = make_target(df=df_i, target=target, target_day=target_day)
        
        # concat result
        df_target = pd.concat([df_target, df_i], axis=0)
        
    return df_target, nb_missing


def mapping_plant_id(x: str, plant_name_id: dict) -> str:
    for p_name, p_id in plant_name_id.items():
        # mapping x using p_name into p_id
        if p_name in x:
            return p_id
    
    return x


def split_train_test_by_month(df: pd.DataFrame, test_period_day: int) -> List[pd.DataFrame]:
    '''
    split data into train and test set per month
    test period is the number of test days from the last day of month
    '''
    
    # define test date range
    test_date = []
    month_list = df.Date.dt.month.unique()
    month_list.sort()
    
    for m in month_list:
        if m == month_list[-1]:
            month_range = pd.date_range(start=f'2021-0{m}-01',end=df['Date'].max(),freq='H')[:-1]
        else:
            month_range = pd.date_range(start=f'2021-0{m}-01',end=f'2021-0{m+1}-01',freq='H')[:-1]
        test_date.extend(month_range[-24*test_period_day:].tolist())

    # split data into train and test set using test date range
    trainset = df[~df['Date'].isin(test_date)]
    testset = df[df['Date'].isin(test_date)]
    
    return trainset, testset


def run(args):
    # read file list
    weather_list = glob(os.path.join(args.weather_dir, '*'))
    plant_list = glob(os.path.join(args.plant_dir, '*'))
    plant_info = pd.read_csv(args.plant_info_path)

    # ==================
    # read plant info
    # ==================
    
    # extract 'si' and 'gun' from 'pp_addr'
    plant_info['si_gun'] = plant_info['pp_addr'].apply(lambda x: x.split(' ')[1][:-1])
    print(f'[READ] plant infomation: {plant_info.shape}')

    # ==================
    # read plant data
    # ==================
    
    # read all plant data and concatenate dataframe
    plant_df = pd.DataFrame()
    nb_missing = 0
    for p_dir in plant_list:
        df_p, nb_missing_p = read_plant_data_and_target(plant_dir=p_dir, target=args.target, target_day=args.target_day)
        
        nb_missing += nb_missing_p
        plant_df = pd.concat([plant_df, df_p], axis=0)

    # mapping values of Plant column into plant id using plant information
    plant_df['Plant'] = plant_df['Plant'].apply(lambda x: mapping_plant_id(
        x             = x,
        plant_name_id = dict(zip(plant_info['pp_name'],plant_info['pp_id']))
    ))

    # change 'Plant' to 'pp_id'
    plant_df = plant_df.rename(columns={'Plant':'pp_id'})
    print(f'[READ] plant data: {plant_df.shape} and total filled missing value: {nb_missing}')
    
    # ==================
    # read weather data
    # ==================
    
    # read all weather data
    weather_df = pd.DataFrame()
    for w_path in weather_list:
        weather_i = pd.read_excel(w_path)
        weather_df = pd.concat([weather_df, weather_i], axis=0)
        
    # mapping 지점명 into 시군(si_gun)
    si_gun_map = {
        '강진군': '영암',
        '목포': '무안',
        '해남': '해남'
    }

    weather_df['si_gun'] = weather_df['지점명'].map(si_gun_map)
    
    
    # change Korean to English column names
    colname_map = {
        '일시'        : 'Date', 
        '기온(°C)'    : 'temp', 
        '강수량(mm)'  : 'precipitation', 
        '풍속(m/s)'   : 'wind_speed', 
        '풍향(16방위)' : 'wind_direction', 
        '습도(%)'     : 'humid',
        '현지기압(hPa)': 'atmo_pressure', 
        '일조(hr)'    : 'sunshine', 
        '일사(MJ/m2)' : 'solar_radiation', 
        '적설(cm)'    : 'snow_cover', 
        '전운량(10분위)': 'cloud_cover', 
        '지면온도(°C)'  : 'ground_temp',
    }

    weather_df = weather_df.rename(columns=colname_map)
    print(f'[READ] weather data: {weather_df.shape}')
    
    
    # ==================
    # merge 
    # ==================
    
    # merge plant data and plant information
    feature_info = ['pp_id','si_gun','pp_lati','pp_longi']
    plant_merged = pd.merge(plant_df, plant_info[feature_info], on=['pp_id'], how='left')
    print(f'[MERGE] plant data and plant information: {plant_merged.shape}')

    # fill NaN with zero(0) and merge plant data and weather data
    feature_weather = list(colname_map.values()) + ['si_gun']
    plant_weather = pd.merge(plant_merged, weather_df[feature_weather].fillna(0), on=['Date','si_gun'], how='inner')
    print(f'[MERGE] merged plant data and weather data: {plant_weather.shape}')


    # ==================
    # cleaning
    # ==================
    
    # drop duplicates because duplicates rows are generated by 'Plant' column in plant data 
    # (ex. 'Plant' column in '.csv' and '.xls' files has difference values)
    plant_weather = plant_weather.drop_duplicates()

    # drop 'su_gun' column
    plant_weather = plant_weather.drop('si_gun', axis=1)
    
    # sorting and re-indexing
    plant_weather = plant_weather.sort_values(['pp_id','Inverter','Date'])
    plant_weather.index = range(len(plant_weather))    
    print(f'[CLEARNING] merged plant data: {plant_weather.shape}')
    
    # ==================
    # split train and test
    # ==================
    trainset, testset = split_train_test_by_month(df=plant_weather, test_period_day=args.test_period_day)
    print(f'[SPLIT] trainset: {trainset.shape}, testset: {testset.shape}')
    
    
    # save
    savedir = os.path.join(args.savedir, f"target_{args.target}-day_{'_'.join(map(str,args.target_day))}-test_period_day_{args.test_period_day}")
    os.makedirs(savedir, exist_ok=True)
    
    trainset.to_csv(os.path.join(savedir, 'train.csv'), index=False)
    testset.to_csv(os.path.join(savedir, 'test.csv'), index=False)
    
    with open(os.path.join(savedir,'shape_info.txt'),'w') as f:
        f.write(f'train shape: {trainset.shape}\n')
        f.write(f'test shape: {testset.shape}\n')
    
    


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Solar Power Generation Forecasting')
    parser.add_argument('--weather_dir', type=str, default='./data/weather', help='weather data directory')
    parser.add_argument('--plant_dir', type=str, default='./data/plant_list', help='plant list directory')
    parser.add_argument('--plant_info_path', type=str, default='./data/plant_info.csv', help='plant information file path')
    
    parser.add_argument('--target', type=str, default='Total Yield(kWh)', help='target name')
    parser.add_argument('--target_day', nargs='+', type=int, default=[1, 7], help='target day for forecasting')
    
    parser.add_argument('--test_period_day', type=int, default=3, help='test period day')
    
    parser.add_argument('--savedir', type=str, default='./preprocessed_data', help='save directory')
    
    args = parser.parse_args()
    
    run(args)
    