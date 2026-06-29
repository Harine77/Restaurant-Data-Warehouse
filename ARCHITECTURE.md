# Project Architecture

```mermaid
flowchart LR
    %% Sources
    subgraph S[Source Data]
        S1[Day 1 CSVs\nsource_data/day_1]
        S2[Day 2 CSVs\nsource_data/day_2]
    end

    %% ETL pipeline
    subgraph E[ETL / Data Prep]
        P1[01_profile_data.py\nProfile raw files]
        P2[02_clean_data.py\nClean & standardize Day 1]
        L1[04_initial_load_day1.py\nInitial warehouse load]
        V1[05_verify_warehouse.py\nValidation checks]
        U1[06_scd1_update.py\nSCD Type 1 changes]
        U2[07_scd2_update.py\nSCD Type 2 history]
        I1[08_incremental_load.py\nNew Day 2 records]
        A1[09_aggregations.py\nBuild summary tables]
    end

    %% Storage
    subgraph D[Warehouse / Storage]
        C1[(Cleaned CSVs\nsource_data/cleaned)]
        DB[(MySQL Database\nrestaurant_dw)]
        D1[dim_date]
        D2[dim_customer]
        D3[dim_menu_item]
        D4[dim_staff]
        F1[fact_order_items]
        G1[agg_daily_revenue]
        G2[agg_item_performance]
        G3[agg_customer_summary]
        G4[agg_staff_performance]
        G5[agg_category_summary]
        G6[agg_monthly_summary]
        G7[agg_loyalty_revenue]
        G8[agg_hourly_orders]
    end

    %% Consumption
    subgraph B[Analytics / BI]
        Dash[10_dashboard.py\nStreamlit dashboard]
    end

    %% Data flow
    S1 --> P1 --> P2 --> C1
    S2 --> U1
    S2 --> U2
    S2 --> I1
    C1 --> L1
    L1 --> DB
    V1 --> DB
    U1 --> DB
    U2 --> DB
    I1 --> DB
    A1 --> DB

    DB --> D1
    DB --> D2
    DB --> D3
    DB --> D4
    DB --> F1
    DB --> G1
    DB --> G2
    DB --> G3
    DB --> G4
    DB --> G5
    DB --> G6
    DB --> G7
    DB --> G8

    DB --> Dash

    %% Styling hints
    classDef source fill:#FFF7E6,stroke:#D97706,color:#111827;
    classDef etl fill:#E8F1FF,stroke:#2563EB,color:#111827;
    classDef store fill:#ECFDF5,stroke:#10B981,color:#111827;
    classDef bi fill:#F3E8FF,stroke:#8B5CF6,color:#111827;

    class S1,S2 source;
    class P1,P2,L1,V1,U1,U2,I1,A1 etl;
    class C1,DB,D1,D2,D3,D4,F1,G1,G2,G3,G4,G5,G6,G7,G8 store;
    class Dash bi;
```

## Overview

- Raw Day 1 data is profiled and cleaned first.
- Cleaned Day 1 data is loaded into the MySQL warehouse.
- Day 2 data drives SCD1 updates, SCD2 history changes, and incremental inserts.
- Aggregation tables are built for fast dashboard queries.
- The Streamlit dashboard reads the warehouse and summary tables directly.

## Main Components

- `source_data/day_1`: raw source files for the first load.
- `source_data/day_2`: changed and new records for updates and incremental loading.
- `restaurant_dw`: MySQL warehouse containing dimensions, fact table, control table, and aggregates.
- `10_dashboard.py`: interactive Streamlit analytics layer.
