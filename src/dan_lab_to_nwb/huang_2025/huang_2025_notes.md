# Notes concerning the huang_2025 conversion

## Miscellaneous
- Info.mat contains various metadata info such as session start time and date
- Most of the content in Notes.txt and StoreListing.txt appear to be replicated in Info.mat --> ignore in favor of the .mat file
- Box1-M301sncCalibrationData.mat is useless -- Don't worry about it.
- Reorganized folders to match expected structure from neo for TDT data.

## LFP
- LFP channels are both EEG (1,2) and EMG (3,4) automatically filtered (and downsampled?) from TDT
- filtering parameters will be shared in an image of the tdt software screen
- EEG electrodes are wires wrapped around a screw in the brain
- EMG electrodes are wires inserted subcutaneously in the neck

## Fiber Photometry
- TODO: Add stub option
- Still need descriptions for Pu1_, Pu2_, PC2_, PC3_, TC1_, TC2_, St1_, St2_, ISI1_, ISI2_
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
- TODO: Update VideoInterface on neuroconv to make it easier to update the descriptions.
- Cam1.onset = Temporal alignment times for camera

## Behavior
- Should be a .mat file with sleep and wake times
- Plan: Load this data into the epochs table

## Pose Estimation
- Should be standard DLC output

## Histology
- Should be a folder of .tiffs for each animal after they have been sacrificed
- Plan: Store each in pynwb.image.GreyscaleImage or pynwb.image.RGBImage
