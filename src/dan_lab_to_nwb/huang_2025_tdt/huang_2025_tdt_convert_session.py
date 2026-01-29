"""Primary script to run to convert an entire session for of data using the NWBConverter."""
import copy
import datetime
import shutil
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from pydantic import DirectoryPath, FilePath
from pymatreader import read_mat

from dan_lab_to_nwb.huang_2025_tdt import Huang2025NWBConverter
from neuroconv.utils import dict_deep_update, load_dict_from_file


def session_to_nwb(
    *,
    info_file_path: FilePath,
    output_dir_path: DirectoryPath,
    video_file_path: FilePath,
    record_fiber: int,
    tdt_fp_folder_path: DirectoryPath,
    tdt_ephys_folder_path: DirectoryPath,
    stream_name: str,
    subject_id: str,
    sex: str,
    dob: str,
    optogenetic_site_name: str,
    optogenetic_virus_volume_in_uL: float,
    fiber_photometry_site_name: str | None = None,
    fiber_photometry_virus_volume_in_uL: float | None = None,
    shared_test_pulse: bool = False,
    stub_test: bool = False,
    verbose: bool = True,
    skip_fiber_photometry: bool = False,
):
    info_file_path = Path(info_file_path)
    video_file_path = Path(video_file_path)
    tdt_fp_folder_path = Path(tdt_fp_folder_path)
    tdt_ephys_folder_path = Path(tdt_ephys_folder_path)
    output_dir_path = Path(output_dir_path)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    source_data = dict()
    conversion_options = dict()

    # Add TDT EEG and EMG
    source_data["EEG"] = dict(
        folder_path=tdt_ephys_folder_path, gain=1.0, stream_name=stream_name, es_key="ElectricalSeriesEEG"
    )
    conversion_options["EEG"] = dict(stub_test=stub_test, group_names=["ElectrodeGroupEEG"])
    source_data["EMG"] = dict(
        folder_path=tdt_ephys_folder_path, gain=1.0, stream_name=stream_name, es_key="ElectricalSeriesEMG"
    )
    conversion_options["EMG"] = dict(stub_test=stub_test, group_names=["ElectrodeGroupEMG"])

    # Add Fiber Photometry
    if not skip_fiber_photometry:
        source_data["FiberPhotometry"] = dict(folder_path=tdt_fp_folder_path)
        conversion_options["FiberPhotometry"] = dict(stub_test=stub_test)

    # Add Video
    if "Cam1" in video_file_path.name:
        video_name = "Video1"
    elif "Cam2" in video_file_path.name:
        video_name = "Video2"
    source_data["Video"] = dict(file_paths=[video_file_path], video_name=video_name)
    conversion_options["Video"] = dict()

    # Add Optogenetics
    source_data["Optogenetics"] = dict(
        folder_path=tdt_fp_folder_path,
        optogenetic_site_name=optogenetic_site_name,
        record_fiber=record_fiber,
        shared_test_pulse=shared_test_pulse,
        virus_volume_in_uL=optogenetic_virus_volume_in_uL,
    )
    conversion_options["Optogenetics"] = dict()

    converter = Huang2025NWBConverter(source_data=source_data, verbose=verbose)
    metadata = converter.get_metadata()

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "huang_2025_tdt_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    info = read_mat(filename=info_file_path)["Info"]
    session_id = info["blockname"]
    pst = ZoneInfo("US/Pacific")
    if "Start" in info:
        session_start_time = datetime.datetime.strptime(info["Start"], "%I:%M:%S%p %m/%d/%Y").replace(tzinfo=pst)
    else:
        date = datetime.datetime.strptime(info["date"], "%Y-%b-%d").date()  # 2025-Apr-09
        time = datetime.datetime.strptime(info["utcStartTime"], "%H:%M:%S").time()  # 14:10:06
        session_start_time_utc = datetime.datetime.combine(date, time).replace(tzinfo=datetime.timezone.utc)
        session_start_time = session_start_time_utc.astimezone(pst)
    nwbfile_path = output_dir_path / f"sub-{subject_id}_ses-{session_id}.nwb"
    metadata["NWBFile"]["session_id"] = session_id
    metadata["Subject"]["subject_id"] = subject_id
    metadata["Subject"]["sex"] = sex
    metadata["Subject"]["date_of_birth"] = dob
    metadata["NWBFile"]["session_start_time"] = session_start_time

    if not skip_fiber_photometry:
        # Update metadata with session-specific details for Fiber Photometry
        fp_metadata = metadata["Ophys"]["FiberPhotometry"]
        filtered_fp_metadata = copy.deepcopy(fp_metadata)
        filtered_fp_metadata["OpticalFibers"] = [
            fiber for fiber in fp_metadata["OpticalFibers"] if fiber_photometry_site_name in fiber["name"]
        ]
        filtered_fp_metadata["FiberPhotometryViruses"] = [
            virus for virus in fp_metadata["FiberPhotometryViruses"] if fiber_photometry_site_name in virus["name"]
        ]
        filtered_fp_metadata["FiberPhotometryVirusInjections"] = []
        for injection_meta in fp_metadata["FiberPhotometryVirusInjections"]:
            injection_meta["volume_in_uL"] = fiber_photometry_virus_volume_in_uL
            if fiber_photometry_site_name in injection_meta["name"]:
                filtered_fp_metadata["FiberPhotometryVirusInjections"].append(injection_meta)
        filtered_fp_metadata["FiberPhotometryIndicators"] = [
            indicator
            for indicator in fp_metadata["FiberPhotometryIndicators"]
            if fiber_photometry_site_name in indicator["name"]
        ]
        filtered_fp_metadata["FiberPhotometryTable"]["rows"] = [
            row for row in fp_metadata["FiberPhotometryTable"]["rows"] if fiber_photometry_site_name in row["location"]
        ]
        if record_fiber == 1:
            for series_meta in filtered_fp_metadata["FiberPhotometryResponseSeries"]:
                if "calcium_signal" in series_meta["name"]:
                    series_meta["stream_name"] = "_465B"
                    series_meta["fiber_photometry_table_region"] = [0]
                elif "isosbestic_control" in series_meta["name"]:
                    series_meta["stream_name"] = "_405B"
                    series_meta["fiber_photometry_table_region"] = [1]
                else:
                    raise ValueError(f"Unrecognized Fiber Photometry series name: {series_meta['name']}")
        elif record_fiber == 2:
            for series_meta in filtered_fp_metadata["FiberPhotometryResponseSeries"]:
                if "calcium_signal" in series_meta["name"]:
                    series_meta["stream_name"] = "_465C"
                    series_meta["fiber_photometry_table_region"] = [0]
                elif "isosbestic_control" in series_meta["name"]:
                    series_meta["stream_name"] = "_405C"
                    series_meta["fiber_photometry_table_region"] = [1]
                else:
                    raise ValueError(f"Unrecognized Fiber Photometry series name: {series_meta['name']}")
        else:
            raise ValueError(f"Unrecognized record_fiber value: {record_fiber}")
        metadata["Ophys"]["FiberPhotometry"] = filtered_fp_metadata

    # Run conversion
    converter.run_conversion(metadata=metadata, nwbfile_path=nwbfile_path, conversion_options=conversion_options)

    if verbose:
        print(f"Session {session_id} for subject {subject_id} converted successfully to NWB format at {nwbfile_path}")


def main():
    # Parameters for conversion
    data_dir_path = Path("/Volumes/T7/CatalystNeuro/Dan/FP and opto datasets")
    output_dir_path = Path("/Volumes/T7/CatalystNeuro/Dan/conversion_nwb/huang_2025_tdt")
    stub_test = True

    if output_dir_path.exists():
        shutil.rmtree(output_dir_path)

    # # opto-signal sum Example Sessions
    # # ------------------------------------------------------------------------------------------------------------------

    # # Setup - Bing
    # # '/Volumes/T7/CatalystNeuro/Dan/FP and opto datasets/Setup - Bing/202409-old setting/M301-240904-072001/Lindsay_SBO_op1-E_2in1_pTra_con-240902-231421/M301-240904-072001'
    # metadata_df = pd.read_csv(
    #     "/Volumes/T7/CatalystNeuro/Dan/FP and opto datasets/metadata/opto-signal sum/Dat-cre_mVTA_3h-stim_low virus - Sheet1.csv"
    # )
    # subject_id = "M301"
    # row = metadata_df[metadata_df["mouse ID"] == subject_id].iloc[0]
    # sex = "M" if row["M"] == 1 else "F"
    # pst = ZoneInfo("US/Pacific")
    # dob = datetime.datetime.strptime(row["DOB"], "%m/%d/%Y").replace(tzinfo=pst)
    # optogenetic_site_name = row["Stim region"]
    # date_column_names = [name for name in metadata_df.columns if name.startswith("date")]
    # record_fiber_column_names = [name for name in metadata_df.columns if name.startswith("Record fiber")]
    # session_index = 0
    # date_column_name = date_column_names[session_index]
    # record_fiber_column_name = record_fiber_column_names[session_index]
    # record_fiber = int(row[record_fiber_column_name])
    # fiber_photometry_site_name = row["Record region"]
    # virus_volume_column_names = [name for name in metadata_df.columns if name.startswith("virus volume")]
    # optogenetic_virus_volume_column_name = virus_volume_column_names[0]
    # fiber_photometry_virus_volume_column_name = virus_volume_column_names[1]
    # optogenetic_virus_volume_in_nL = float(
    #     row[optogenetic_virus_volume_column_name].replace("nL", "")
    # )  # 300nL --> 300.0
    # optogenetic_virus_volume_in_uL = optogenetic_virus_volume_in_nL / 1000.0
    # fiber_photometry_virus_volume_in_nL = float(
    #     row[fiber_photometry_virus_volume_column_name].replace("nL", "")
    # )  # 300nL --> 300.0
    # fiber_photometry_virus_volume_in_uL = fiber_photometry_virus_volume_in_nL / 1000.0

    # info_file_path = (
    #     data_dir_path
    #     / "Setup - Bing"
    #     / "202409-old setting"
    #     / "M301-240904-072001"
    #     / "Lindsay_SBO_op1-E_2in1_pTra_con-240902-231421"
    #     / "M301-240904-072001"
    #     / "Info.mat"
    # )
    # video_file_path = (
    #     data_dir_path
    #     / "Setup - Bing"
    #     / "202409-old setting"
    #     / "M301-240904-072001"
    #     / "Lindsay_SBO_op1-E_2in1_pTra_con-240902-231421"
    #     / "M301-240904-072001"
    #     / "Lindsay_SBO_op1-E_2in1_pTra_con-240902-231421_M301-240904-072001_Cam1.avi"
    # )
    # tdt_fp_folder_path = (
    #     data_dir_path
    #     / "Setup - Bing"
    #     / "202409-old setting"
    #     / "M301-240904-072001"
    #     / "Lindsay_SBO_op1-E_2in1_pTra_con-240902-231421"
    #     / "M301-240904-072001"
    # )
    # tdt_ephys_folder_path = (
    #     data_dir_path
    #     / "Setup - Bing"
    #     / "202409-old setting"
    #     / "M301-240904-072001"
    #     / "Lindsay_SBO_op1-E_2in1_pTra_con-240902-231421"
    # )
    # session_to_nwb(
    #     info_file_path=info_file_path,
    #     video_file_path=video_file_path,
    #     tdt_fp_folder_path=tdt_fp_folder_path,
    #     record_fiber=record_fiber,
    #     tdt_ephys_folder_path=tdt_ephys_folder_path,
    #     output_dir_path=output_dir_path,
    #     subject_id=subject_id,
    #     sex=sex,
    #     dob=dob,
    #     optogenetic_site_name=optogenetic_site_name,
    #     fiber_photometry_site_name=fiber_photometry_site_name,
    #     stub_test=stub_test,
    #     stream_name="LFP1",
    #     optogenetic_virus_volume_in_uL=optogenetic_virus_volume_in_uL,
    #     fiber_photometry_virus_volume_in_uL=fiber_photometry_virus_volume_in_uL,
    # )

    # # Setup - WS8
    # # /Volumes/T7/CatalystNeuro/Dan/FP and opto datasets/Setup - WS8/202404/202410/M296-241018-072001/Lindsay_SBO_op1-E_2in1_pTra_con-241017-190451/M296-241018-072001
    # metadata_df = pd.read_csv(
    #     "/Volumes/T7/CatalystNeuro/Dan/FP and opto datasets/metadata/opto-signal sum/Dat-cre_mVTA_3h-stim_low virus - Sheet1.csv"
    # )
    # subject_id = "M296"
    # row = metadata_df[metadata_df["mouse ID"] == subject_id].iloc[0]
    # sex = "M" if row["M"] == 1 else "F"
    # pst = ZoneInfo("US/Pacific")
    # dob = datetime.datetime.strptime(row["DOB"], "%m/%d/%Y").replace(tzinfo=pst)
    # optogenetic_site_name = row["Stim region"]
    # date_column_names = [name for name in metadata_df.columns if name.startswith("date")]
    # record_fiber_column_names = [name for name in metadata_df.columns if name.startswith("Record fiber")]
    # session_index = 0
    # date_column_name = date_column_names[session_index]
    # record_fiber_column_name = record_fiber_column_names[session_index]
    # record_fiber = int(row[record_fiber_column_name])
    # fiber_photometry_site_name = row["Record region"]
    # virus_volume_column_names = [name for name in metadata_df.columns if name.startswith("virus volume")]
    # optogenetic_virus_volume_column_name = virus_volume_column_names[0]
    # fiber_photometry_virus_volume_column_name = virus_volume_column_names[1]
    # optogenetic_virus_volume_in_nL = float(
    #     row[optogenetic_virus_volume_column_name].replace("nL", "")
    # )  # 300nL --> 300.0
    # optogenetic_virus_volume_in_uL = optogenetic_virus_volume_in_nL / 1000.0
    # fiber_photometry_virus_volume_in_nL = float(
    #     row[fiber_photometry_virus_volume_column_name].replace("nL", "")
    # )  # 300nL --> 300.0
    # fiber_photometry_virus_volume_in_uL = fiber_photometry_virus_volume_in_nL / 1000.0
    # info_file_path = (
    #     data_dir_path
    #     / "Setup - WS8"
    #     / "202404"
    #     / "202410"
    #     / "M296-241018-072001"
    #     / "Lindsay_SBO_op1-E_2in1_pTra_con-241017-190451"
    #     / "M296-241018-072001"
    #     / "Info.mat"
    # )
    # video_file_path = (
    #     data_dir_path
    #     / "Setup - WS8"
    #     / "202404"
    #     / "202410"
    #     / "M296-241018-072001"
    #     / "Lindsay_SBO_op1-E_2in1_pTra_con-241017-190451"
    #     / "M296-241018-072001"
    #     / "Lindsay_SBO_op1-E_2in1_pTra_con-241017-190451_M296-241018-072001_Cam1.avi"
    # )
    # tdt_fp_folder_path = (
    #     data_dir_path
    #     / "Setup - WS8"
    #     / "202404"
    #     / "202410"
    #     / "M296-241018-072001"
    #     / "Lindsay_SBO_op1-E_2in1_pTra_con-241017-190451"
    #     / "M296-241018-072001"
    # )
    # tdt_ephys_folder_path = (
    #     data_dir_path
    #     / "Setup - WS8"
    #     / "202404"
    #     / "202410"
    #     / "M296-241018-072001"
    #     / "Lindsay_SBO_op1-E_2in1_pTra_con-241017-190451"
    # )
    # session_to_nwb(
    #     info_file_path=info_file_path,
    #     video_file_path=video_file_path,
    #     tdt_fp_folder_path=tdt_fp_folder_path,
    #     record_fiber=record_fiber,
    #     tdt_ephys_folder_path=tdt_ephys_folder_path,
    #     stream_name="LFP1",
    #     output_dir_path=output_dir_path,
    #     subject_id=subject_id,
    #     sex=sex,
    #     dob=dob,
    #     optogenetic_site_name=optogenetic_site_name,
    #     fiber_photometry_site_name=fiber_photometry_site_name,
    #     optogenetic_virus_volume_in_uL=optogenetic_virus_volume_in_uL,
    #     fiber_photometry_virus_volume_in_uL=fiber_photometry_virus_volume_in_uL,
    #     stub_test=stub_test,
    # )

    # # Setup - MollyFP first subject
    # # Note: this example session actually contains data from two subjects, but only one is included in the NWB file.
    # # /Volumes/T7/CatalystNeuro/Dan/FP and opto datasets/Setup - MollyFP/MollyFP-202508/M363_M366-250822-153604/A_Lindsay_TDTm_op1_pTra_2min-250822-153604/M363_M366-250822-153604
    # metadata_df = pd.read_csv(
    #     "/Volumes/T7/CatalystNeuro/Dan/FP and opto datasets disorganized/metadata/opto-signal sum/Sert-cre_DRN_2min-pTra-stim - GS - Sheet1.csv"
    # )
    # subject_id = "M363"
    # row = metadata_df[metadata_df["mouse ID"] == subject_id].iloc[0]
    # sex = "M" if row["M"] == 1 else "F"
    # pst = ZoneInfo("US/Pacific")
    # dob = datetime.datetime.strptime(row["DOB"], "%m/%d/%Y").replace(tzinfo=pst)
    # optogenetic_site_name = row["Stim region"]
    # fiber_photometry_site_name = row["Record region"]
    # record_fiber = 1
    # shared_test_pulse = True
    # virus_volume_column_names = [name for name in metadata_df.columns if name.startswith("virus volume")]
    # optogenetic_virus_volume_column_name = virus_volume_column_names[0]
    # fiber_photometry_virus_volume_column_name = virus_volume_column_names[1]
    # optogenetic_virus_volume_in_nL = float(
    #     row[optogenetic_virus_volume_column_name].replace("nL", "")
    # )  # 300nL --> 300.0
    # optogenetic_virus_volume_in_uL = optogenetic_virus_volume_in_nL / 1000.0
    # fiber_photometry_virus_volume_in_nL = float(
    #     row[fiber_photometry_virus_volume_column_name].replace("nL", "")
    # )  # 300nL --> 300.0
    # fiber_photometry_virus_volume_in_uL = fiber_photometry_virus_volume_in_nL / 1000.0
    # info_file_path = (
    #     data_dir_path
    #     / "Setup - MollyFP"
    #     / "MollyFP-202508"
    #     / "M363_M366-250822-153604"
    #     / "A_Lindsay_TDTm_op1_pTra_2min-250822-153604"
    #     / "M363_M366-250822-153604"
    #     / "Info.mat"
    # )
    # video_file_path = (
    #     data_dir_path
    #     / "Setup - MollyFP"
    #     / "MollyFP-202508"
    #     / "M363_M366-250822-153604"
    #     / "A_Lindsay_TDTm_op1_pTra_2min-250822-153604"
    #     / "M363_M366-250822-153604"
    #     / "A_Lindsay_TDTm_op1_pTra_2min-250822-153604_M363_M366-250822-153604_Cam1.avi"
    # )
    # tdt_fp_folder_path = (
    #     data_dir_path
    #     / "Setup - MollyFP"
    #     / "MollyFP-202508"
    #     / "M363_M366-250822-153604"
    #     / "A_Lindsay_TDTm_op1_pTra_2min-250822-153604"
    #     / "M363_M366-250822-153604"
    # )
    # tdt_ephys_folder_path = (
    #     data_dir_path
    #     / "Setup - MollyFP"
    #     / "MollyFP-202508"
    #     / "M363_M366-250822-153604"
    #     / "A_Lindsay_TDTm_op1_pTra_2min-250822-153604"
    # )
    # session_to_nwb(
    #     info_file_path=info_file_path,
    #     video_file_path=video_file_path,
    #     tdt_fp_folder_path=tdt_fp_folder_path,
    #     tdt_ephys_folder_path=tdt_ephys_folder_path,
    #     stream_name="LFP1",
    #     output_dir_path=output_dir_path,
    #     subject_id=subject_id,
    #     sex=sex,
    #     dob=dob,
    #     optogenetic_site_name=optogenetic_site_name,
    #     fiber_photometry_site_name=fiber_photometry_site_name,
    #     record_fiber=record_fiber,
    #     optogenetic_virus_volume_in_uL=optogenetic_virus_volume_in_uL,
    #     fiber_photometry_virus_volume_in_uL=fiber_photometry_virus_volume_in_uL,
    #     shared_test_pulse=shared_test_pulse,
    #     stub_test=stub_test,
    # )

    # # Setup - MollyFP second subject
    # # Note: this example session actually contains data from two subjects, but only one is included in the NWB file.
    # # /Volumes/T7/CatalystNeuro/Dan/FP and opto datasets/Setup - MollyFP/MollyFP-202508/M363_M366-250822-153604/A_Lindsay_TDTm_op1_pTra_2min-250822-153604/M363_M366-250822-153604
    # metadata_df = pd.read_csv(
    #     "/Volumes/T7/CatalystNeuro/Dan/FP and opto datasets disorganized/metadata/opto-signal sum/Sert-cre_DRN_2min-pTra-stim - GS - Sheet1.csv"
    # )
    # subject_id = "M366"
    # row = metadata_df[metadata_df["mouse ID"] == subject_id].iloc[0]
    # sex = "M" if row["M"] == 1 else "F"
    # pst = ZoneInfo("US/Pacific")
    # dob = datetime.datetime.strptime(row["DOB"], "%m/%d/%Y").replace(tzinfo=pst)
    # optogenetic_site_name = row["Stim region"]
    # fiber_photometry_site_name = row["Record region"]
    # record_fiber = 2
    # shared_test_pulse = True
    # virus_volume_column_names = [name for name in metadata_df.columns if name.startswith("virus volume")]
    # optogenetic_virus_volume_column_name = virus_volume_column_names[0]
    # fiber_photometry_virus_volume_column_name = virus_volume_column_names[1]
    # optogenetic_virus_volume_in_nL = float(
    #     row[optogenetic_virus_volume_column_name].replace("nL", "")
    # )  # 300nL --> 300.0
    # optogenetic_virus_volume_in_uL = optogenetic_virus_volume_in_nL / 1000.0
    # fiber_photometry_virus_volume_in_nL = float(
    #     row[fiber_photometry_virus_volume_column_name].replace("nL", "")
    # )  # 300nL --> 300.0
    # fiber_photometry_virus_volume_in_uL = fiber_photometry_virus_volume_in_nL / 1000.0
    # info_file_path = (
    #     data_dir_path
    #     / "Setup - MollyFP"
    #     / "MollyFP-202508"
    #     / "M363_M366-250822-153604"
    #     / "A_Lindsay_TDTm_op1_pTra_2min-250822-153604"
    #     / "M363_M366-250822-153604"
    #     / "Info.mat"
    # )
    # video_file_path = (
    #     data_dir_path
    #     / "Setup - MollyFP"
    #     / "MollyFP-202508"
    #     / "M363_M366-250822-153604"
    #     / "A_Lindsay_TDTm_op1_pTra_2min-250822-153604"
    #     / "M363_M366-250822-153604"
    #     / "A_Lindsay_TDTm_op1_pTra_2min-250822-153604_M363_M366-250822-153604_Cam2.avi"
    # )
    # tdt_fp_folder_path = (
    #     data_dir_path
    #     / "Setup - MollyFP"
    #     / "MollyFP-202508"
    #     / "M363_M366-250822-153604"
    #     / "A_Lindsay_TDTm_op1_pTra_2min-250822-153604"
    #     / "M363_M366-250822-153604"
    # )
    # tdt_ephys_folder_path = (
    #     data_dir_path
    #     / "Setup - MollyFP"
    #     / "MollyFP-202508"
    #     / "M363_M366-250822-153604"
    #     / "A_Lindsay_TDTm_op1_pTra_2min-250822-153604"
    # )
    # session_to_nwb(
    #     info_file_path=info_file_path,
    #     video_file_path=video_file_path,
    #     tdt_fp_folder_path=tdt_fp_folder_path,
    #     tdt_ephys_folder_path=tdt_ephys_folder_path,
    #     stream_name="LFP2",
    #     output_dir_path=output_dir_path,
    #     subject_id=subject_id,
    #     sex=sex,
    #     dob=dob,
    #     optogenetic_site_name=optogenetic_site_name,
    #     fiber_photometry_site_name=fiber_photometry_site_name,
    #     record_fiber=record_fiber,
    #     shared_test_pulse=shared_test_pulse,
    #     optogenetic_virus_volume_in_uL=optogenetic_virus_volume_in_uL,
    #     fiber_photometry_virus_volume_in_uL=fiber_photometry_virus_volume_in_uL,
    #     stub_test=stub_test,
    # )

    # opto-behavioral sum Example Sessions
    # ------------------------------------------------------------------------------------------------------------------
    # Setup - Bing
    # '/Volumes/T7/CatalystNeuro/Dan/FP and opto datasets/Setup - Bing/202408-old setting/M008-240819-071001/Lindsay_SBO_opto1-Evoke12_2in1-240817-154318_BBB8-240819-071001/M008-240819-071001'
    metadata_df = pd.read_csv(
        "/Volumes/T7/CatalystNeuro/Dan/FP and opto datasets/metadata/opto-behavioral sum/ChAT-cre_BF_2min-20Hz-stim - GS - Sheet1.csv"
    )
    subject_id = "M008"
    row = metadata_df[metadata_df["mouse ID"] == subject_id].iloc[0]
    sex = "M" if row["M"] == 1 else "F"
    pst = ZoneInfo("US/Pacific")
    dob = datetime.datetime.strptime(row["DOB"], "%m/%d/%Y").replace(tzinfo=pst)
    optogenetic_site_name = row["Stim region"]
    record_fiber = 1
    virus_volume_column_names = [name for name in metadata_df.columns if name.startswith("virus volume")]
    optogenetic_virus_volume_column_name = virus_volume_column_names[0]
    optogenetic_virus_volume_in_nL = float(
        row[optogenetic_virus_volume_column_name].replace("nL", "")
    )  # 300nL --> 300.0
    optogenetic_virus_volume_in_uL = optogenetic_virus_volume_in_nL / 1000.0
    info_file_path = (
        data_dir_path
        / "Setup - Bing"
        / "202408-old setting"
        / "BBB8-240819-071001"
        / "Lindsay_SBO_opto1-Evoke12_2in1-240817-154318"
        / "BBB8-240819-071001"
        / "Info.mat"
    )
    video_file_path = (
        data_dir_path
        / "Setup - Bing"
        / "202408-old setting"
        / "BBB8-240819-071001"
        / "Lindsay_SBO_opto1-Evoke12_2in1-240817-154318"
        / "BBB8-240819-071001"
        / "Lindsay_SBO_opto1-Evoke12_2in1-240817-154318_BBB8-240819-071001_Cam1.avi"
    )
    tdt_fp_folder_path = (
        data_dir_path
        / "Setup - Bing"
        / "202408-old setting"
        / "BBB8-240819-071001"
        / "Lindsay_SBO_opto1-Evoke12_2in1-240817-154318"
        / "BBB8-240819-071001"
    )
    tdt_ephys_folder_path = (
        data_dir_path
        / "Setup - Bing"
        / "202408-old setting"
        / "BBB8-240819-071001"
        / "Lindsay_SBO_opto1-Evoke12_2in1-240817-154318"
    )
    session_to_nwb(
        info_file_path=info_file_path,
        video_file_path=video_file_path,
        tdt_ephys_folder_path=tdt_ephys_folder_path,
        tdt_fp_folder_path=tdt_fp_folder_path,
        stream_name="LFP1",
        output_dir_path=output_dir_path,
        subject_id=subject_id,
        sex=sex,
        dob=dob,
        optogenetic_site_name=optogenetic_site_name,
        record_fiber=record_fiber,
        optogenetic_virus_volume_in_uL=optogenetic_virus_volume_in_uL,
        stub_test=stub_test,
        skip_fiber_photometry=True,
    )

    # Setup - WS8
    # '/Volumes/T7/CatalystNeuro/Dan/FP and opto datasets disorganized/Setup - WS8/WS8-202504/M303_M042-250430-082001'

    # Setup - MollyFP
    # '/Volumes/T7/CatalystNeuro/Dan/FP and opto datasets disorganized/Setup - MollyFP/MollyFP-202507/M363_M364-250721-191039'


if __name__ == "__main__":
    main()
