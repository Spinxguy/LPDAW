import sys
import pygame
from pygame import mixer
import tkinter as tk
from tkinter import ttk
from pydub import AudioSegment
from pydub.playback import play
from threading import Thread
from tkinter.filedialog import asksaveasfilename

class LPDAW:
    def __init__(self, root):
        self.root = root
        self.root.title("Lightweight Python DAW")

        # Initialize pygame mixer
        mixer.init()

        # BPM and playback settings
        self.bpm = 120
        self.is_playing = False
        self.step_index = 0
        self.num_steps = 16  # Number of steps in the channel rack
        self.channels = []
        self.selected_channel = None

        # UI Elements
        self.create_widgets()

    def create_widgets(self):
        # BPM Control
        bpm_frame = ttk.Frame(self.root)
        bpm_frame.pack(pady=5)
        ttk.Label(bpm_frame, text="BPM:").pack(side=tk.LEFT)
        self.bpm_var = tk.IntVar(value=self.bpm)
        bpm_spinbox = ttk.Spinbox(bpm_frame, from_=30, to=300, textvariable=self.bpm_var, width=5, command=self.update_bpm)
        bpm_spinbox.pack(side=tk.LEFT)

        # Add Channel Button
        add_channel_button = ttk.Button(self.root, text="Add Channel", command=self.add_channel)
        add_channel_button.pack(pady=5)

        # Delete Channel Button
        delete_channel_button = ttk.Button(self.root, text="Delete Channel", command=self.delete_channel)
        delete_channel_button.pack(pady=5)

        # Export Button
        export_button = ttk.Button(self.root, text="Export to WAV", command=self.export_to_wav)
        export_button.pack(pady=5)

        # Open Mixer Button
        mixer_button = ttk.Button(self.root, text="Open Mixer", command=self.open_mixer)
        mixer_button.pack(pady=5)

        # Channel Rack Frame
        self.channel_rack_frame = ttk.Frame(self.root)
        self.channel_rack_frame.pack(pady=5)

        # Play/Stop Buttons
        control_frame = ttk.Frame(self.root)
        control_frame.pack(pady=5)
        self.play_button = ttk.Button(control_frame, text="Play", command=self.toggle_playback)
        self.play_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(control_frame, text="Stop", command=self.stop_playback)
        self.stop_button.pack(side=tk.LEFT, padx=5)

    def add_channel(self):
        channel = Channel(self.channel_rack_frame, self.num_steps)
        self.channels.append(channel)

    def delete_channel(self):
        if self.channels:
            channel_to_delete = self.channels.pop()
            channel_to_delete.frame.destroy()

    def update_bpm(self):
        self.bpm = self.bpm_var.get()

    def toggle_playback(self):
        if self.is_playing:
            self.is_playing = False
            self.play_button.config(text="Play")
        else:
            self.is_playing = True
            self.play_button.config(text="Pause")
            self.start_playback()

    def start_playback(self):
        if not self.is_playing:
            return

        step_duration = 60 / self.bpm / 4  # 16th note duration
        for channel in self.channels:
            channel.play_step(self.step_index)

        self.step_index = (self.step_index + 1) % self.num_steps
        self.root.after(int(step_duration * 1000), self.start_playback)

    def stop_playback(self):
        self.is_playing = False
        self.play_button.config(text="Play")
        self.step_index = 0
        for channel in self.channels:
            channel.stop_all()

    def open_mixer(self):
        if not self.channels:
            return

        mixer_window = tk.Toplevel(self.root)
        mixer_window.title("Mixer")

        ttk.Label(mixer_window, text="Select Channel:").pack(pady=5)
        self.channel_selector = ttk.Combobox(mixer_window, state="readonly")
        self.channel_selector.pack(pady=5)
        self.channel_selector['values'] = [f"Channel {i+1}" for i in range(len(self.channels))]
        self.channel_selector.bind("<<ComboboxSelected>>", self.select_channel)

        ttk.Label(mixer_window, text="Volume:").pack(pady=5)
        self.mixer_volume_var = tk.DoubleVar()
        self.mixer_volume_scale = ttk.Scale(mixer_window, from_=0.0, to=1.0, variable=self.mixer_volume_var, command=self.update_mixer_volume)
        self.mixer_volume_scale.pack(pady=5)

        ttk.Button(mixer_window, text="Open Pitcher", command=self.open_pitcher).pack(pady=5)

    def select_channel(self, event):
        selected_index = self.channel_selector.current()
        if selected_index >= 0:
            self.selected_channel = self.channels[selected_index]
            self.mixer_volume_var.set(self.selected_channel.volume)

    def update_mixer_volume(self, _):
        if self.selected_channel:
            self.selected_channel.volume = self.mixer_volume_var.get()

    def open_pitcher(self):
        if not self.selected_channel:
            return

        pitcher_window = tk.Toplevel(self.root)
        pitcher_window.title("Pitcher")

        ttk.Label(pitcher_window, text="Pitch Adjustment (semitones):").pack(pady=5)
        self.pitch_var = tk.IntVar(value=0)
        pitch_scale = ttk.Scale(pitcher_window, from_=-12, to=12, variable=self.pitch_var, orient=tk.HORIZONTAL, command=self.update_pitch)
        pitch_scale.pack(pady=5)

    def update_pitch(self, _):
        if self.selected_channel:
            self.selected_channel.adjust_pitch(self.pitch_var.get())

    def export_to_wav(self):
        output_file = asksaveasfilename(defaultextension=".wav", filetypes=[("WAV Files", "*.wav")])
        if not output_file:
            return

        final_mix = AudioSegment.silent(duration=60 / self.bpm * self.num_steps * 1000)

        for channel in self.channels:
            if channel.original_sound:
                track = AudioSegment.silent(duration=0)
                for step_index, step_active in enumerate(channel.steps):
                    if step_active:
                        start_time = (60 / self.bpm / 4) * step_index * 1000
                        track += AudioSegment.silent(duration=start_time - len(track))
                        track += channel.sound
                final_mix = final_mix.overlay(track)

        final_mix.export(output_file, format="wav")
        print(f"Exported to {output_file}")

class Channel:
    def __init__(self, parent, num_steps):
        self.num_steps = num_steps
        self.volume = 0.5
        self.sound = None
        self.original_sound = None  # For pitch adjustments
        self.steps = [False] * num_steps

        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.X, pady=2)

        # Sound File Selection
        self.sound_button = ttk.Button(self.frame, text="Load Sound", command=self.load_sound)
        self.sound_button.pack(side=tk.LEFT)

        # Step Buttons
        self.step_buttons = []
        for i in range(num_steps):
            step_button = ttk.Checkbutton(self.frame, command=lambda i=i: self.toggle_step(i))
            step_button.pack(side=tk.LEFT, padx=1)
            self.step_buttons.append(step_button)

    def load_sound(self):
        from tkinter.filedialog import askopenfilename
        file_path = askopenfilename(
            filetypes=[
                ("Audio Files", "*.wav *.mp3"),
                ("WAV Files", "*.wav"),
                ("MP3 Files", "*.mp3"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            try:
                self.original_sound = AudioSegment.from_file(file_path)
                self.sound = self.original_sound
                self.sound_button.config(text=file_path.split("/")[-1])
            except Exception as e:
                print(f"Failed to load sound: {e}")

    def toggle_step(self, index):
        self.steps[index] = not self.steps[index]

    def play_step(self, step_index):
        if self.steps[step_index] and self.sound:
            Thread(target=self._play_sound).start()

    def _play_sound(self):
        play(self.sound - (1 - self.volume) * 60)

    def stop_all(self):
        pass  # Not implemented for pydub

    def adjust_pitch(self, semitones):
        if self.original_sound:
            self.sound = self.original_sound._spawn(self.original_sound.raw_data, overrides={
                "frame_rate": int(self.original_sound.frame_rate * (2 ** (semitones / 12.0)))
            }).set_frame_rate(self.original_sound.frame_rate)

if __name__ == "__main__":
    root = tk.Tk()
    app = LPDAW(root)
    root.mainloop()
