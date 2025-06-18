from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QSoundEffect

from ClassicLib.Constants import YAML
from ClassicLib.YamlSettingsCache import classic_settings, yaml_settings


class AudioPlayer(QObject):
    """
    The AudioPlayer class manages the playback of audio notifications, providing sound
    effects for error, notification, and custom events. It enables or disables audio
    based on settings and connects signals to play corresponding sounds.

    This class uses QSoundEffect to handle pre-defined and custom audio files. The
    playback of sounds can be toggled on or off using the toggle_audio method.

    Attributes:
        play_error_signal (Signal): Signal to trigger error sound playback.
        play_notify_signal (Signal): Signal to trigger notification sound playback.
        play_custom_signal (Signal): Signal to play a custom sound file with a specified path.
    """

    # Constants
    DEFAULT_VOLUME = 0.5
    SOUND_DIR = "CLASSIC Data/sounds"
    ERROR_SOUND_PATH: str = f"{SOUND_DIR}/classic_error.wav"
    NOTIFY_SOUND_PATH: str = f"{SOUND_DIR}/classic_notify.wav"
    SETTING_KEY: str = "Audio Notifications"
    SETTING_PATH: str = f"CLASSIC_Settings.{SETTING_KEY}"

    # Signals for different sounds
    play_error_signal: Signal = Signal()
    play_notify_signal: Signal = Signal()
    play_custom_signal: Signal = Signal(str)

    def __init__(self) -> None:
        """
        Initialize audio notification settings and prepare sound effects.
        If audio notification setting is not configured, sets a default value.
        """
        super().__init__()

        # Initialize audio settings
        self.audio_enabled = classic_settings(bool, self.SETTING_KEY)
        if self.audio_enabled is None:
            yaml_settings(bool, YAML.Settings, self.SETTING_PATH, True)
            self.audio_enabled = True

        # Setup sound effects
        self.error_sound = self._initialize_sound(self.ERROR_SOUND_PATH)
        self.notify_sound = self._initialize_sound(self.NOTIFY_SOUND_PATH)

        # Connect signals if audio is enabled
        self._manage_signal_connections(connect=self.audio_enabled)

    def _initialize_sound(self, sound_path: str) -> QSoundEffect:
        """
        Initialize a QSoundEffect with the given sound path and default volume.

        Args:
            sound_path (str): Path to the sound file.

        Returns:
            QSoundEffect: Initialized sound effect object.
        """
        sound: QSoundEffect = QSoundEffect()
        sound.setSource(QUrl.fromLocalFile(sound_path))
        sound.setVolume(self.DEFAULT_VOLUME)
        return sound

    def _manage_signal_connections(self, connect: bool) -> None:
        """
        Connect or disconnect all signal-slot pairs based on the connect parameter.

        Args:
            connect (bool): If True, connect signals; otherwise, disconnect them.
        """
        if connect:
            self.play_error_signal.connect(self.play_error_sound)
            self.play_notify_signal.connect(self.play_notify_sound)
            self.play_custom_signal.connect(self.play_custom_sound)
        else:
            self.play_error_signal.disconnect()
            self.play_notify_signal.disconnect()
            self.play_custom_signal.disconnect()

    def play_error_sound(self) -> None:
        """
        Play the error sound if audio is enabled and the sound is loaded.
        """
        if self.audio_enabled and self.error_sound.isLoaded():
            self.error_sound.play()

    def play_notify_sound(self) -> None:
        """
        Play the notification sound if audio is enabled and the sound is loaded.
        """
        if self.audio_enabled and self.notify_sound.isLoaded():
            self.notify_sound.play()

    @staticmethod
    def play_custom_sound(sound_path: str, volume: float = 1.0) -> None:
        """
        Play a custom sound effect from the specified file path.

        Args:
            sound_path (str): The file path of the sound file to play.
            volume (float, optional): Volume level (0.0 to 1.0). Defaults to 1.0.
        """
        custom_sound: QSoundEffect = QSoundEffect()
        custom_sound.setSource(QUrl.fromLocalFile(sound_path))
        custom_sound.setVolume(volume)
        custom_sound.play()

    def toggle_audio(self, state: bool) -> None:
        """
        Toggle audio functionality, enabling or disabling sound signals.

        Args:
            state (bool): If True, enable audio; otherwise, disable it.
        """
        self.audio_enabled = state
        self._manage_signal_connections(connect=state)
