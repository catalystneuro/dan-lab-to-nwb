# Notes concerning the dan_lab_to_nwb conversion project

## Miscellaneous
- Info.mat contains various metadata info such as session start time and date
- Most of the content in Notes.txt and StoreListing.txt appear to be replicated in Info.mat --> ignore in favor of the .mat file
- Box1-M301sncCalibrationData.mat is useless -- Don't worry about it.
- Reorganized folders to match expected structure from neo for TDT data.
- The following sessions do not have video nor fiber photometry and will be excluded from the final dataset, skipping:
    'M405_M407-250412-081001(done)',
    'M404_M409-250406-141501(done)',
    'M404_M409-250405-151801(done)',
    'M405_M407-250412-142001(done)',
    'M404-M409-250406-153701 (M404 bad signal, done)',
    'M405_M407-250413-081001(done)',
    'M405_M407-250413-152101(done)',
    'M409_M404-250407-153704 (done)',
    'M405_M407-250414-081001(done)'

## LFP
- LFP channels are both EEG (1,2) and EMG (3,4) automatically filtered (and downsampled?) from TDT
- filtering parameters were shared in an image of the tdt software screen
- EEG electrodes are wires wrapped around a screw in the brain
- EMG electrodes are wires inserted subcutaneously in the neck
- In TDT EEG and EMG data are 2 channels each, but in the .mat files, they each only have one channel

## Fiber Photometry
- 465B and 465C correspond to 2 different fibers: One in VTA and the other in PFC
- But other experimental protocols use different locations for the 2 fibers (SNC and/or striatum)

## Optogenetics
- power is always 20mW
- channel 1 = 465B/405B = usually VTA
- channel 2 = 465C/405C = usually PFC (sometimes striatum)

For file names containing "pTra_con":
- TC1_ is the onset of channel 1 fiber photometry imaging.
- TC2_ is the onset of channel 2 fiber photometry imaging.
- St1_ is the channel 1 test pulse. (50ms) ISI1, Pu1_ and PC2_ are duplicated info of St1_. I only use St1_ for analysis.
- St2_ is the channel 2 test pulse. (50ms) ISI2, Pu2_ and PC3_ are duplicated info of St2_. I only use St2_ for analysis.
- So basically you can ignore  ISI1, Pu1_, PC2_, ISI2, Pu2_, and PC3_, which I never use.
- Wi1_ is the window of applying intense stimulation, which contains bursts of pulses. (the window is typically 3 hour)
- Laser is On during St1/St2 and Wi3.
- LasT is the burst window, which contains 5 laser pulses. (200ms)
- Wi3_ is the laser pulse (LS). (4ms each LS)

For file names containing "opto":
- TC1_ is the onset of channel 1 fiber photometry imaging.
- TC2_ is the onset of channel 2 fiber photometry imaging.
- St1_ is the channel 1 test pulse. (50ms) ISI1, Pu1_ and PC0_ are duplicated info of St1_. I only use St1_ for analysis.
- St2_ is the channel 2 test pulse. (50ms) ISI2, Pu2_ and PC3_ are duplicated info of St2_. I only use St2_ for analysis.
- So basically you can ignore  ISI1, Pu1_, PC0_, ISI2, Pu2_, and PC3_, which I never use.
- Wi1_ is the window of applying intense stimulation, which contains 20Hz pulses. (the window is typically 2min)
- LasT is the pulse. (10ms)
- Laser is On during St1/St2 and LasT

## Video
- Cam1.onset = Temporal alignment times for camera (Cam1.onset is located in the tdt data)
- But, for Lindsay_SBO_op1-E_2in1_pTra_con-241101-072001/M301-241108-072001, len(Cam1.onset) = 257944 ≠ number of frames = 257953

## Behavior
- Labels is an array with 3 values (1, 2, 3) with shape (2878,) which matches neither the number of video/dlc frames (143946,) nor the EEG data (14642688,)
- The labels start from time 0, and each label covers 5s. At the end of the video file, the residual data less than 5 seconds will be discarded.
- There is also a behavioral summary file which lists
    - t_LM = time spent in locomotion
    - t_NL = time spent doing non-locomotive movements
    - t_QW = time spent in quiet wakefulness
    - t_NREM = time spent in non-rem sleep
    - t_REM = time spent in rem sleep
    - distance_out_of_nest = total distance traveled while out of the nest (cm?)
    - distance_in_nest = total distance traveled while in the nest (cm?)
    - time_in_nest = time spent in the nest
    - time_out_of_nest = time spent out of the nest
    - session = S1 or S2 or etc.

## Pose Estimation
- Standard DLC output (.h5)
- "Both of them [video and ephys] are aligned to the starting time as time 0."

## Histology
- Should be a folder of .tiffs for each animal after they have been sacrificed
- Plan: Store each in pynwb.image.GreyscaleImage or pynwb.image.RGBImage


## Active Questions/Requests
- Temporal Alignment
    - Length mismatch for TDT video temporal alignment?
    - ephys-video temporal alignment for dlc data?
- Fiber Optic Cables
    - Are there separate cables for fiber photometry and optogenetics or do they share?
    - Need fiber insertion coordinates for optogenetics
- In the optogenetics metadata questionnaire, I have locations listed for VTA, basal forebrain, and locus coeruleus. But in our email, we had talked about the VTA and PFC. Do we have data with PFC optogenetics? Are we going to get a subject mapping?
- edges for DLC?
