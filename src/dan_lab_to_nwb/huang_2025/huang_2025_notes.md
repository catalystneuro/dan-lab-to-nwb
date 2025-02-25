# Notes concerning the huang_2025 conversion

## Miscellaneous
- Info.mat contains various metadata info such as session start time and date
- Most of the content in Notes.txt and StoreListing.txt appear to be replicated in Info.mat --> ignore in favor of the .mat file
- What is Box1-M301sncCalibrationData.mat?
- Reorganized folders to match expected structure from neo for TDT data.
- Where is EMG data?

## LFP
- Are the lfp channels eeg?
- Where are the electrodes?
- Need device and location metadata
- Is it filtered or raw acquisition?

## Fiber Photometry
- TODO: Add stub option
- What are all the different store_ids? Opto? Commanded Voltage? 465B vs 465C?
- St1_ = Stim 1 = optogenetic stimulation?
- Or Pu1_ = Pulse Generator 1 = optogenetic stimulation?
- Or LasT = optogenetic stimulation?
- Cam1 = Temporal alignment times for camera???

## Video
- TODO: Update VideoInterface on neuroconv to make it easier to update the descriptions.

## Behavior
- There's behavioral video, but no pose estimation or processed behavioral data. Likely that the lab does this analysis
    but hasn't shared. At the very least there should be sleep and wake times.

## Histology
- Noted in the kickoff meeting, but not shared in the data.
