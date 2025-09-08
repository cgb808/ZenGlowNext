# Training Data Structure

## Directory Organization

### `/data/raw/`

- Place your raw wellness data files here
- Supported formats: CSV, JSON, Parquet
- Expected files:
  - `physiological_data.csv` - Heart rate, HRV, steps, etc.
  - `behavioral_data.csv` - App usage, interactions, etc.
  - `mood_data.csv` - Self-reported mood, journal entries
  - `contextual_data.csv` - Time, location, activities

### Available Datasets

#### UCI HAR Dataset (Human Activity Recognition Using Smartphones)

- **Location**: `UCI HAR Dataset/`
- **Description**: Smartphone sensor data for activity recognition
- **Activities**: WALKING, WALKING_UPSTAIRS, WALKING_DOWNSTAIRS, SITTING, STANDING, LAYING
- **Sensors**: Accelerometer and Gyroscope (3-axial)
- **Subjects**: 30 volunteers (19-48 years)
- **Features**: 561 time and frequency domain features
- **Train/Test Split**: Pre-split into training (70%) and test (30%) sets
- **Use Case**: Perfect for training child activity monitoring models

### `/data/processed/`

- Cleaned and preprocessed data
- Feature engineered datasets
- Train/validation/test splits

### `/data/synthetic/`

- Generated synthetic data for bootstrapping
- Augmented datasets
- Privacy-preserved samples

## Expected Data Schema

### Physiological Data

```csv
timestamp,device_id,heart_rate,hrv,steps,activity_level,stress_indicator
2025-08-11T10:00:00Z,child_001,75,45.2,120,moderate,0.3
```

### Behavioral Data

```csv
timestamp,device_id,screen_time,app_interactions,response_time,notification_count
2025-08-11T10:00:00Z,child_001,15,8,2.5,3
```

### Mood Data

```csv
timestamp,device_id,mood_score,confidence,text_input,wellness_self_report
2025-08-11T10:00:00Z,child_001,0.7,0.85,"Had a good day",8
```

### Contextual Data

```csv
timestamp,device_id,hour_of_day,day_of_week,location_type,is_school_day
2025-08-11T10:00:00Z,child_001,10,6,home,false
```

## Data Requirements

### Minimum Dataset Size

- **Training**: 1000+ samples per child
- **Validation**: 200+ samples per child
- **Test**: 200+ samples per child

### Temporal Coverage

- At least 2 weeks of continuous data
- Include weekdays and weekends
- Cover different times of day

### Quality Requirements

- Missing data < 10%
- Consistent sampling intervals
- Labeled wellness outcomes

---

## 📊 MHEALTH Dataset Integration

### About the MHEALTH Dataset

The **MHEALTH Dataset** from the University of Granada provides comprehensive mobile health data perfect for wellness prediction models.

**Dataset Characteristics:**

- **Subjects**: 10 volunteers of diverse profiles
- **Activities**: 12 different physical activities
- **Sensors**: 23 sensor channels including:
  - Accelerometer (chest, left ankle, right arm)
  - Gyroscope (chest, left ankle, right arm)
  - Magnetometer (chest, left ankle, right arm)
  - ECG sensor (chest)

**Sensor Mapping for Wellness Features:**

```python
# MHEALTH → ZenGlow Feature Mapping
mhealth_mapping = {
    # Physiological
    'chest_acc_x/y/z': 'activity_level',
    'chest_gyro_x/y/z': 'movement_patterns',
    'ecg': 'heart_rate_derived',

    # Activity Recognition
    'ankle_acc_x/y/z': 'steps_estimation',
    'arm_acc_x/y/z': 'gesture_patterns',

    # Wellness Indicators
    'activity_labels': 'baseline_activity',
    'sensor_fusion': 'stress_indicators'
}
```

### MHEALTH Data Preprocessing for ZenGlow

**Step 1: Download MHEALTH Dataset**

```bash
# Download from UCI ML Repository or MHEALTH project site
wget https://archive.ics.uci.edu/ml/datasets/mhealth
# Extract to data/raw/mhealth/
```

**Step 2: Convert to ZenGlow Schema**

```python
# Convert MHEALTH format to ZenGlow wellness features
python training/preprocess_mhealth.py \
    --input data/raw/mhealth/ \
    --output data/processed/wellness_features.csv
```

**Step 3: Generate Family Profiles**

```python
# Create synthetic family wellness patterns based on MHEALTH baselines
python training/generate_family_data.py \
    --baseline data/processed/wellness_features.csv \
    --families 100 \
    --children_per_family 2-4
```

### Citation Requirements

When using MHEALTH data, **you must cite**:

```bibtex
@inproceedings{banos2014mhealthdroid,
  title={mHealthDroid: a novel framework for agile development of mobile health applications},
  author={Banos, O. and Garcia, R. and Holgado, J. A. and Damas, M. and Pomares, H. and Rojas, I. and Saez, A. and Villalonga, C.},
  booktitle={IWAAL 2014},
  year={2014}
}

@article{banos2015design,
  title={Design, implementation and validation of a novel open framework for agile development of mobile health applications},
  author={Banos, O. and Villalonga, C. and Garcia, R. and Saez, A. and Damas, M. and Holgado, J. A. and Lee, S. and Pomares, H. and Rojas, I.},
  journal={BioMedical Engineering OnLine},
  volume={14},
  number={S2:S6},
  pages={1-20},
  year={2015}
}
```

**Contact**: Please inform oresti.bl@gmail.com of publications using this dataset.

### Privacy and Ethics

- ✅ MHEALTH data used under academic research provisions
- ✅ No personal identifiers retained in processed data
- ✅ Synthetic family data generated to protect privacy
- ✅ All processing done locally on-device
- ✅ Parental consent required for family wellness monitoring
