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
- LasT is optogenetic test pulse
- Wi1_ and Wi3_ are longer "intense" optogenetic pulses
- power = 20mW
- stim is cts

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
