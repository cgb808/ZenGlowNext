# 🏥 MHEALTH Dataset Quick Start Guide

## Download and Setup

### 1. Download MHEALTH Dataset
```bash
# Option 1: UCI ML Repository
wget https://archive.ics.uci.edu/ml/machine-learning-databases/00319/MHEALTHDATASET.zip
unzip MHEALTHDATASET.zip -d data/raw/mhealth/

# Option 2: Direct from research team
# Contact: oresti.bl@gmail.com for dataset access
```

### 2. Verify Dataset Structure
```bash
# Expected files in data/raw/mhealth/:
ls data/raw/mhealth/
# Should see: mHealth_subject1.log, mHealth_subject2.log, ..., mHealth_subject10.log
```

### 3. Process MHEALTH Data
```bash
# Convert MHEALTH sensor data to ZenGlow wellness features
python training/preprocess_mhealth.py \
    --input data/raw/mhealth/ \
    --output data/processed/wellness_features.csv
```

### 4. Train TensorFlow Lite Model
```bash
# Train wellness prediction model
python training/train_model.py
```

## MHEALTH Dataset Overview

**Subjects**: 10 volunteers (diverse age, gender, fitness levels)
**Duration**: Multiple recording sessions per subject
**Sensors**: 23 channels from 3 body positions:
- **Chest**: Accelerometer, ECG, Gyroscope, Magnetometer
- **Left Ankle**: Accelerometer, Gyroscope, Magnetometer  
- **Right Arm**: Accelerometer, Gyroscope, Magnetometer

**Activities**: 12 labeled activities:
1. Standing still
2. Sitting and relaxing  
3. Lying down
4. Walking
5. Climbing stairs
6. Waist bends forward
7. Frontal elevation of arms
8. Knees bending (crouching)
9. Cycling
10. Jogging
11. Running
12. Jump front & back

## ZenGlow Wellness Features Extracted

From MHEALTH sensor data, we derive:

### Physiological
- **Heart Rate**: Estimated from ECG signal
- **HRV**: Heart rate variability from ECG
- **Activity Level**: From accelerometer patterns
- **Steps/Minute**: From ankle accelerometer
- **Movement Variance**: Motion consistency

### Behavioral Proxies
- **Activity Intensity**: Overall movement level
- **Movement Consistency**: Pattern regularity
- **Posture Stability**: From gyroscope data

### Wellness Score
- **Combined Score** (0-1): Weighted combination of:
  - Activity level (40%)
  - Physiological stability (30%) 
  - Movement patterns (30%)

## Citation Requirements

**Always cite these papers when using MHEALTH data:**

```bibtex
@inproceedings{banos2014mhealthdroid,
  title={mHealthDroid: a novel framework for agile development of mobile health applications},
  author={Banos, O. and Garcia, R. and Holgado, J. A. and Damas, M. and Pomares, H. and Rojas, I. and Saez, A. and Villalonga, C.},
  booktitle={Proceedings of the 6th International Work-conference on Ambient Assisted Living an Active Ageing (IWAAL 2014)},
  location={Belfast, Northern Ireland},
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

## Expected Output

After processing, you'll have:
- **~50,000+ wellness feature vectors** (depends on dataset size)
- **10 different subject profiles** for model training
- **Realistic activity patterns** for family wellness modeling
- **Validated sensor-to-wellness mappings** for wearable deployment

## Next Steps

1. **Train your model** with real MHEALTH data
2. **Validate accuracy** on holdout test subjects
3. **Convert to TensorFlow Lite** for wearable deployment
4. **Deploy to devices** and compare with MHEALTH baselines

## Contact

- **MHEALTH Dataset**: oresti.bl@gmail.com
- **ZenGlow Implementation**: See project documentation
