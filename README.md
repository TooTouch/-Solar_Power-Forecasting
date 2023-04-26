# Solar_Power-Forecasting
BK21 Hackathon 2023 in Korea University

# Data tree

```
data
├── 기상데이터
├── 발전량 변환
├── 발전소 테이블.csv
└── 발전소 테이블.xls
```

# Preprocessing

## Identifier

발전량 데이터는 아래 두 identifier에 따라 데이터가 수집되어 있음

1. '발전소 테이블.csv'의 `발전소 ID(pp_id)`
2. '발전량 변환' 내 파일의 `Inverter`

## Process

**Plant data**
- 시간 단위로 데이터 정리
- target은 일(day)를 기준으로 생성 (ex. 하루 뒤 or 일주일 뒤)
- 발전소 내 `Inverter` 별 중간에 데이터가 수집이 안된 일자(date)의 경우 'ffill' -> 'bfill' 순으로 처리함

**Weahter data**
- 기상 데이터는 모두 사용
- 결측치는 0으로 처리


**Table merge**

1. 발전소 변환 데이터와 발전소 테이블은 `pp_id`를 기준으로 merge
2. 앞선 결과 데이터의 `pp_addr`과 기상 데이터의 `지점명`을 통해 시군(`si_gun`)을 추출하여 merge

## Data split

- train과 test로 분리
- testset은 월(month) 별 마지막 날짜를 기준으로 사전에 정의한 일(day) 수 만큼 사용


## Run

**Case1**
- target: 하루 뒤 발전량
- test period: 매월 마지막일 기준 그전 3일

```{bash}
python main.py --target_day 1 --test_period_day 3 --savedir ./preprocessed_data
```

**Case2**
- target: 일주일 뒤 발전량
- test period: 매월 마지막일 기준 그전 3일

```{bash}
python main.py --target_day 7 --test_period_day 3 --savedir ./preprocessed_data
```

**Case3**
- target: 하루 뒤 발전량 and 일주일 뒤 발전량
- test period: 매월 마지막일 기준 그전 3일

```{bash}
python main.py --target_day 1 7 --test_period_day 3 --savedir ./preprocessed_data
```

## Results

Case | target day | test period | train size | test size
---|---|---|---|---
Case1 | 1 | 3 | 219,044 | 25,056
Case2 | 7 | 3 | 209,252 | 25,056
Case3 | 1, 7 | 3 | 209,252 | 25,056



