"""Primary NWBConverter class for this dataset."""
from dan_lab_to_nwb.huang_2025_001711 import (
    Huang2025BehaviorInterface,
    Huang2025EcephysMatInterface,
)
from neuroconv import NWBConverter
from neuroconv.datainterfaces import (
    DeepLabCutInterface,
    ExternalVideoInterface,
)


class Huang2025NWBConverter(NWBConverter):
    """
    Primary conversion class for Huang 2025 001711 dataset.

    This NWBConverter combines multiple data streams from behavioral experiments
    that include video recordings, DeepLabCut pose tracking, behavioral annotations,
    and electrophysiology (EEG/EMG) recordings into a single NWB file.

    Attributes
    ----------
    data_interface_classes : dict
        Dictionary mapping data stream names to their respective interface classes.
        Includes Video, DeepLabCut, Behavior, and Ecephys interfaces.

    Notes
    -----
    The converter automatically handles temporal alignment between the video
    timestamps and DeepLabCut pose estimation data.
    """

    data_interface_classes = dict(
        Video=ExternalVideoInterface,
        DeepLabCut=DeepLabCutInterface,
        Behavior=Huang2025BehaviorInterface,
        Ecephys=Huang2025EcephysMatInterface,
    )

    def temporally_align_data_interfaces(self, metadata: dict | None = None, conversion_options: dict | None = None):
        """
        Align DeepLabCut timestamps to match video timestamps.

        This method ensures that the pose estimation data from DeepLabCut is
        temporally synchronized with the video recording timestamps.

        Parameters
        ----------
        metadata : dict or None, optional
            Metadata dictionary (not used in this method but required by parent class).
        conversion_options : dict or None, optional
            Conversion options dictionary (not used in this method but required by parent class).

        Returns
        -------
        None
        """
        video_timestamps = self.data_interface_objects["Video"].get_timestamps()[0]
        self.data_interface_objects["DeepLabCut"].set_aligned_timestamps(video_timestamps)
