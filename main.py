#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio, Gdk, GdkPixbuf
import os
import threading
import shutil
import subprocess
import json
from pathlib import Path
import tempfile
import webbrowser

try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

class HwPlymouther(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.malikhw47.hwplymouther')
        
        # App data
        self.theme_name = ""
        self.theme_desc = ""
        self.input_file = ""
        self.aspect_handling = "center"  # center, stretch, fill
        self.animation_mode = "loop"  # loop, times, boot_progress
        self.play_times = 1
        self.frames = []
        self.output_dir = ""
        
    def do_activate(self):
        self.main_window = MainWindow(self)
        self.main_window.present()

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.app = app
        
        self.set_title("HwPlymouther")
        self.set_default_size(800, 600)
        
        # Create header bar
        self.header_bar = Adw.HeaderBar()
        self.set_titlebar(self.header_bar)
        
        # Add title with subtitle
        title_widget = Adw.WindowTitle()
        title_widget.set_title("HwPlymouther")
        title_widget.set_subtitle("by MalikHw47")
        self.header_bar.set_title_widget(title_widget)
        
        # Add Ko-fi donation button
        kofi_button = Gtk.Button()
        kofi_button.set_icon_name("emblem-favorite-symbolic")
        kofi_button.set_tooltip_text("Support on Ko-fi: MalikHw47")
        kofi_button.connect("clicked", self.on_kofi_clicked)
        self.header_bar.pack_end(kofi_button)
        
        # Add YouTube subscribe button
        youtube_button = Gtk.Button()
        youtube_button.set_icon_name("applications-multimedia-symbolic")
        youtube_button.set_tooltip_text("Subscribe on YouTube")
        youtube_button.connect("clicked", self.on_youtube_clicked)
        self.header_bar.pack_end(youtube_button)
        
        # Create main stack
        self.stack = Adw.ViewStack()
        self.set_content(self.stack)
        
        # Create pages
        self.create_welcome_page()
        self.create_style_page()
        self.create_working_page()
        self.create_complete_page()
        
        # Show welcome page
        self.stack.set_visible_child_name("welcome")
    
    def on_kofi_clicked(self, button):
        webbrowser.open("https://ko-fi.com/malikhw47")
    
    def on_youtube_clicked(self, button):
        webbrowser.open("https://www.youtube.com/@MalikHw47")
    
    def create_welcome_page(self):
        page = Adw.StatusPage()
        page.set_title("Welcome to HwPlymouther")
        page.set_description("Create beautiful Plymouth boot themes from your animations")
        page.set_icon_name("applications-graphics-symbolic")
        
        # Main content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content_box.set_halign(Gtk.Align.CENTER)
        content_box.set_valign(Gtk.Align.CENTER)
        content_box.set_margin_top(40)
        content_box.set_margin_bottom(40)
        content_box.set_margin_start(40)
        content_box.set_margin_end(40)
        
        # Theme name entry
        name_group = Adw.PreferencesGroup()
        name_group.set_title("Theme Information")
        
        self.name_row = Adw.EntryRow()
        self.name_row.set_title("Theme Name")
        self.name_row.connect("changed", self.on_name_changed)
        name_group.add(self.name_row)
        
        self.desc_row = Adw.EntryRow()
        self.desc_row.set_title("Theme Description")
        self.desc_row.connect("changed", self.on_desc_changed)
        name_group.add(self.desc_row)
        
        content_box.append(name_group)
        
        # File selection
        file_group = Adw.PreferencesGroup()
        file_group.set_title("Animation File")
        file_group.set_description("Select a GIF, MP4, or image file")
        
        file_row = Adw.ActionRow()
        file_row.set_title("Select File")
        
        self.file_button = Gtk.Button()
        self.file_button.set_label("Choose File...")
        self.file_button.connect("clicked", self.on_file_clicked)
        self.file_button.set_valign(Gtk.Align.CENTER)
        file_row.add_suffix(self.file_button)
        
        self.file_label = Gtk.Label()
        self.file_label.set_text("No file selected")
        self.file_label.set_halign(Gtk.Align.START)
        file_row.set_subtitle_widget(self.file_label)
        
        file_group.add(file_row)
        content_box.append(file_group)
        
        # Aspect ratio handling (initially hidden)
        self.aspect_group = Adw.PreferencesGroup()
        self.aspect_group.set_title("Aspect Ratio Handling")
        self.aspect_group.set_description("Your image is not 16:9. How should it be handled?")
        self.aspect_group.set_visible(False)
        
        self.aspect_row = Adw.ComboRow()
        self.aspect_row.set_title("Handling Method")
        
        aspect_model = Gtk.StringList()
        aspect_model.append("Center (keep original size)")
        aspect_model.append("Stretch (fit to screen)")
        aspect_model.append("Fill (crop to fit)")
        
        self.aspect_row.set_model(aspect_model)
        self.aspect_row.set_selected(0)
        self.aspect_row.connect("notify::selected", self.on_aspect_changed)
        
        self.aspect_group.add(self.aspect_row)
        content_box.append(self.aspect_group)
        
        # Next button
        self.next_button = Gtk.Button()
        self.next_button.set_label("Next: Style Settings")
        self.next_button.add_css_class("suggested-action")
        self.next_button.set_sensitive(False)
        self.next_button.connect("clicked", self.on_next_style)
        content_box.append(self.next_button)
        
        page.set_child(content_box)
        self.stack.add_titled(page, "welcome", "Welcome")
    
    def create_style_page(self):
        page = Adw.StatusPage()
        page.set_title("Style Settings")
        page.set_description("Configure how your animation will play")
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content_box.set_halign(Gtk.Align.CENTER)
        content_box.set_valign(Gtk.Align.CENTER)
        content_box.set_margin_top(40)
        content_box.set_margin_bottom(40)
        content_box.set_margin_start(40)
        content_box.set_margin_end(40)
        
        # Animation mode
        mode_group = Adw.PreferencesGroup()
        mode_group.set_title("Animation Mode")
        
        self.mode_row = Adw.ComboRow()
        self.mode_row.set_title("Playback Mode")
        
        mode_model = Gtk.StringList()
        mode_model.append("Loop continuously")
        mode_model.append("Play specific number of times")
        mode_model.append("Progress-based (experimental)")
        
        self.mode_row.set_model(mode_model)
        self.mode_row.set_selected(0)
        self.mode_row.connect("notify::selected", self.on_mode_changed)
        
        mode_group.add(self.mode_row)
        content_box.append(mode_group)
        
        # Times setting (initially hidden)
        self.times_group = Adw.PreferencesGroup()
        self.times_group.set_title("Playback Times")
        self.times_group.set_visible(False)
        
        self.times_row = Adw.SpinRow()
        self.times_row.set_title("Number of times to play")
        adjustment = Gtk.Adjustment(value=1, lower=1, upper=100, step_increment=1)
        self.times_row.set_adjustment(adjustment)
        self.times_row.connect("changed", self.on_times_changed)
        
        self.times_group.add(self.times_row)
        content_box.append(self.times_group)
        
        # Navigation buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.CENTER)
        
        back_button = Gtk.Button()
        back_button.set_label("Back")
        back_button.connect("clicked", self.on_back_welcome)
        button_box.append(back_button)
        
        generate_button = Gtk.Button()
        generate_button.set_label("Generate Theme")
        generate_button.add_css_class("suggested-action")
        generate_button.connect("clicked", self.on_generate)
        button_box.append(generate_button)
        
        content_box.append(button_box)
        
        page.set_child(content_box)
        self.stack.add_titled(page, "style", "Style")
    
    def create_working_page(self):
        self.working_page = Adw.StatusPage()
        self.working_page.set_title("Generating Theme...")
        self.working_page.set_description("Please wait while your Plymouth theme is being created")
        self.working_page.set_icon_name("emblem-synchronizing-symbolic")
        
        # Progress indicator
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_pulse_step(0.1)
        self.progress_bar.set_margin_top(20)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content_box.set_halign(Gtk.Align.CENTER)
        content_box.set_valign(Gtk.Align.CENTER)
        content_box.append(self.progress_bar)
        
        self.status_label = Gtk.Label()
        self.status_label.set_text("Initializing...")
        content_box.append(self.status_label)
        
        self.working_page.set_child(content_box)
        self.stack.add_titled(self.working_page, "working", "Working")
    
    def create_complete_page(self):
        self.complete_page = Adw.StatusPage()
        self.complete_page.set_title("Theme Generated!")
        self.complete_page.set_icon_name("emblem-ok-symbolic")
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content_box.set_halign(Gtk.Align.CENTER)
        content_box.set_valign(Gtk.Align.CENTER)
        
        # Output location
        self.output_label = Gtk.Label()
        self.output_label.set_selectable(True)
        self.output_label.set_wrap(True)
        content_box.append(self.output_label)
        
        # Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.CENTER)
        
        open_folder_button = Gtk.Button()
        open_folder_button.set_label("Open Folder")
        open_folder_button.connect("clicked", self.on_open_folder)
        button_box.append(open_folder_button)
        
        new_theme_button = Gtk.Button()
        new_theme_button.set_label("Create New Theme")
        new_theme_button.add_css_class("suggested-action")
        new_theme_button.connect("clicked", self.on_new_theme)
        button_box.append(new_theme_button)
        
        content_box.append(button_box)
        
        self.complete_page.set_child(content_box)
        self.stack.add_titled(self.complete_page, "complete", "Complete")
    
    def on_name_changed(self, entry):
        self.app.theme_name = entry.get_text()
        self.update_next_button()
    
    def on_desc_changed(self, entry):
        self.app.theme_desc = entry.get_text()
    
    def update_next_button(self):
        can_proceed = bool(self.app.theme_name and self.app.input_file)
        self.next_button.set_sensitive(can_proceed)
    
    def on_file_clicked(self, button):
        dialog = Gtk.FileChooserDialog(
            title="Select Animation File",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            "Cancel", Gtk.ResponseType.CANCEL,
            "Select", Gtk.ResponseType.ACCEPT
        )
        
        # Add file filters
        filter_all = Gtk.FileFilter()
        filter_all.set_name("Supported Files")
        filter_all.add_mime_type("image/gif")
        filter_all.add_mime_type("video/mp4")
        filter_all.add_mime_type("image/png")
        filter_all.add_mime_type("image/jpeg")
        dialog.add_filter(filter_all)
        
        filter_gif = Gtk.FileFilter()
        filter_gif.set_name("GIF Images")
        filter_gif.add_mime_type("image/gif")
        dialog.add_filter(filter_gif)
        
        filter_video = Gtk.FileFilter()
        filter_video.set_name("Video Files")
        filter_video.add_mime_type("video/mp4")
        dialog.add_filter(filter_video)
        
        filter_image = Gtk.FileFilter()
        filter_image.set_name("Image Files")
        filter_image.add_mime_type("image/png")
        filter_image.add_mime_type("image/jpeg")
        dialog.add_filter(filter_image)
        
        dialog.connect("response", self.on_file_dialog_response)
        dialog.present()
    
    def on_file_dialog_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            file = dialog.get_file()
            if file:
                self.app.input_file = file.get_path()
                filename = os.path.basename(self.app.input_file)
                self.file_label.set_text(f"Selected: {filename}")
                
                # Check aspect ratio for images/videos
                self.check_aspect_ratio()
                self.update_next_button()
        
        dialog.destroy()
    
    def check_aspect_ratio(self):
        """Check if the file has 16:9 aspect ratio"""
        try:
            if self.app.input_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                # For images, check with GdkPixbuf
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(self.app.input_file)
                width = pixbuf.get_width()
                height = pixbuf.get_height()
            elif HAS_OPENCV and self.app.input_file.lower().endswith(('.gif', '.mp4')):
                # For videos/gifs, check with OpenCV
                cap = cv2.VideoCapture(self.app.input_file)
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()
            else:
                # Can't check, assume it's fine
                self.aspect_group.set_visible(False)
                return
            
            # Check if it's roughly 16:9 (allow some tolerance)
            aspect_ratio = width / height
            target_ratio = 16 / 9
            tolerance = 0.1
            
            if abs(aspect_ratio - target_ratio) > tolerance:
                self.aspect_group.set_visible(True)
            else:
                self.aspect_group.set_visible(False)
                
        except Exception as e:
            print(f"Error checking aspect ratio: {e}")
            self.aspect_group.set_visible(False)
    
    def on_aspect_changed(self, combo, param):
        selected = combo.get_selected()
        if selected == 0:
            self.app.aspect_handling = "center"
        elif selected == 1:
            self.app.aspect_handling = "stretch"
        elif selected == 2:
            self.app.aspect_handling = "fill"
    
    def on_next_style(self, button):
        self.stack.set_visible_child_name("style")
    
    def on_mode_changed(self, combo, param):
        selected = combo.get_selected()
        if selected == 0:
            self.app.animation_mode = "loop"
            self.times_group.set_visible(False)
        elif selected == 1:
            self.app.animation_mode = "times"
            self.times_group.set_visible(True)
        elif selected == 2:
            self.app.animation_mode = "boot_progress"
            self.times_group.set_visible(False)
    
    def on_times_changed(self, spin):
        self.app.play_times = int(spin.get_value())
    
    def on_back_welcome(self, button):
        self.stack.set_visible_child_name("welcome")
    
    def on_generate(self, button):
        self.stack.set_visible_child_name("working")
        # Start generation in a separate thread
        thread = threading.Thread(target=self.generate_theme)
        thread.daemon = True
        thread.start()
    
    def generate_theme(self):
        """Generate the Plymouth theme"""
        try:
            GLib.idle_add(self.update_progress, "Creating output directory...")
            
            # Create output directory
            base_dir = os.path.expanduser("~/Documents/HwPlymouther")
            os.makedirs(base_dir, exist_ok=True)
            
            theme_dir = os.path.join(base_dir, self.app.theme_name)
            if os.path.exists(theme_dir):
                shutil.rmtree(theme_dir)
            os.makedirs(theme_dir)
            
            self.app.output_dir = theme_dir
            
            GLib.idle_add(self.update_progress, "Extracting frames...")
            
            # Extract frames
            self.extract_frames()
            
            GLib.idle_add(self.update_progress, "Creating Plymouth files...")
            
            # Create Plymouth theme files
            self.create_plymouth_files()
            
            GLib.idle_add(self.update_progress, "Complete!")
            GLib.idle_add(self.on_generation_complete)
            
        except Exception as e:
            GLib.idle_add(self.on_generation_error, str(e))
    
    def extract_frames(self):
        """Extract frames from the input file"""
        self.app.frames = []
        
        if self.app.input_file.lower().endswith(('.png', '.jpg', '.jpeg')):
            # Single image
            self.app.frames = [self.app.input_file]
        elif HAS_OPENCV:
            # Video or GIF
            cap = cv2.VideoCapture(self.app.input_file)
            frame_count = 0
            
            temp_dir = os.path.join(self.app.output_dir, "frames_temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Save frame
                frame_path = os.path.join(temp_dir, f"frame_{frame_count:04d}.png")
                cv2.imwrite(frame_path, frame)
                self.app.frames.append(frame_path)
                frame_count += 1
            
            cap.release()
        else:
            raise Exception("OpenCV not available for video/GIF processing")
    
    def create_plymouth_files(self):
        """Create Plymouth theme configuration files"""
        
        # Copy and process frames
        frames_dir = os.path.join(self.app.output_dir, "frames")
        os.makedirs(frames_dir, exist_ok=True)
        
        processed_frames = []
        for i, frame_path in enumerate(self.app.frames):
            if frame_path.startswith(os.path.join(self.app.output_dir, "frames_temp")):
                # Temporary frame, move it
                dest_path = os.path.join(frames_dir, f"frame_{i:04d}.png")
                shutil.move(frame_path, dest_path)
            else:
                # Original file, copy it
                dest_path = os.path.join(frames_dir, f"frame_{i:04d}.png")
                shutil.copy2(frame_path, dest_path)
            
            processed_frames.append(f"frames/frame_{i:04d}.png")
        
        # Clean up temp directory
        temp_dir = os.path.join(self.app.output_dir, "frames_temp")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        
        # Create theme configuration
        theme_config = {
            "name": self.app.theme_name,
            "description": self.app.theme_desc,
            "frames": processed_frames,
            "mode": self.app.animation_mode,
            "times": self.app.play_times if self.app.animation_mode == "times" else None,
            "aspect_handling": self.app.aspect_handling
        }
        
        # Write theme.plymouth file
        plymouth_content = f"""[Plymouth Theme]
Name={self.app.theme_name}
Description={self.app.theme_desc}
ModuleName=script

[script]
ImageDir={os.path.join(self.app.output_dir)}
ScriptFile={os.path.join(self.app.output_dir, f"{self.app.theme_name}.script")}
"""
        
        with open(os.path.join(self.app.output_dir, f"{self.app.theme_name}.plymouth"), 'w') as f:
            f.write(plymouth_content)
        
        # Create script file
        script_content = self.generate_script_content(processed_frames)
        with open(os.path.join(self.app.output_dir, f"{self.app.theme_name}.script"), 'w') as f:
            f.write(script_content)
        
        # Write configuration JSON for reference
        with open(os.path.join(self.app.output_dir, "theme_config.json"), 'w') as f:
            json.dump(theme_config, f, indent=2)
        
        # Create installation instructions
        install_instructions = f"""# {self.app.theme_name} Plymouth Theme

## Installation Instructions

1. Copy this entire folder to /usr/share/plymouth/themes/:
   ```
   sudo cp -r "{self.app.output_dir}" /usr/share/plymouth/themes/
   ```

2. Set as default theme:
   ```
   sudo plymouth-set-default-theme {self.app.theme_name}
   ```

3. Update initramfs:
   ```
   sudo update-initramfs -u
   ```

## Theme Details
- Name: {self.app.theme_name}
- Description: {self.app.theme_desc}
- Frames: {len(processed_frames)}
- Mode: {self.app.animation_mode}
- Generated by HwPlymouther by MalikHw47
"""
        
        with open(os.path.join(self.app.output_dir, "README.md"), 'w') as f:
            f.write(install_instructions)
    
    def generate_script_content(self, frames):
        """Generate the Plymouth script content"""
        
        script = f'''// {self.app.theme_name} Plymouth Script
// Generated by HwPlymouther by MalikHw47

// Load images
images = [];
'''
        
        for i, frame in enumerate(frames):
            script += f'images[{i}] = Image("{frame}");\n'
        
        script += f'''
// Screen setup
screen_width = Window.GetWidth();
screen_height = Window.GetHeight();

// Animation variables
frame_count = {len(frames)};
current_frame = 0;
animation_time = 0;
'''
        
        if self.app.animation_mode == "loop":
            script += '''
// Continuous loop mode
fun refresh_callback() {
    current_frame = (current_frame + 1) % frame_count;
    
    sprite = Sprite(images[current_frame]);
    sprite.SetX((screen_width - images[current_frame].GetWidth()) / 2);
    sprite.SetY((screen_height - images[current_frame].GetHeight()) / 2);
    
    Plymouth.SetRefreshRate(10); // 10 FPS
}

Plymouth.SetRefreshFunction(refresh_callback);
'''
        elif self.app.animation_mode == "times":
            script += f'''
// Play specific number of times
play_times = {self.app.play_times};
current_play = 0;
animation_complete = 0;

fun refresh_callback() {{
    if (animation_complete) return;
    
    current_frame++;
    
    if (current_frame >= frame_count) {{
        current_play++;
        if (current_play >= play_times) {{
            animation_complete = 1;
            current_frame = frame_count - 1; // Stay on last frame
        }} else {{
            current_frame = 0; // Restart animation
        }}
    }}
    
    sprite = Sprite(images[current_frame]);
    sprite.SetX((screen_width - images[current_frame].GetWidth()) / 2);
    sprite.SetY((screen_height - images[current_frame].GetHeight()) / 2);
    
    Plymouth.SetRefreshRate(10); // 10 FPS
}}

Plymouth.SetRefreshFunction(refresh_callback);
'''
        else:  # boot_progress mode
            script += '''
// Progress-based animation
fun refresh_callback() {
    progress = Plymouth.GetBootProgress();
    target_frame = Math.Int(progress * frame_count);
    if (target_frame >= frame_count) target_frame = frame_count - 1;
    
    sprite = Sprite(images[target_frame]);
    sprite.SetX((screen_width - images[target_frame].GetWidth()) / 2);
    sprite.SetY((screen_height - images[target_frame].GetHeight()) / 2);
}

Plymouth.SetRefreshFunction(refresh_callback);
'''
        
        return script
    
    def update_progress(self, message):
        self.status_label.set_text(message)
        self.progress_bar.pulse()
    
    def on_generation_complete(self):
        self.complete_page.set_description(f"Your Plymouth theme '{self.app.theme_name}' has been successfully created!")
        self.output_label.set_text(f"Theme location:\n{self.app.output_dir}")
        self.stack.set_visible_child_name("complete")
    
    def on_generation_error(self, error_msg):
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Generation Error",
            body=f"An error occurred while generating the theme:\n\n{error_msg}"
        )
        dialog.add_response("ok", "OK")
        dialog.present()
        self.stack.set_visible_child_name("style")
    
    def on_open_folder(self, button):
        subprocess.run(["xdg-open", self.app.output_dir])
    
    def on_new_theme(self, button):
        # Reset app state
        self.app.theme_name = ""
        self.app.theme_desc = ""
        self.app.input_file = ""
        self.app.aspect_handling = "center"
        self.app.animation_mode = "loop"
        self.app.play_times = 1
        self.app.frames = []
        self.app.output_dir = ""
        
        # Reset UI
        self.name_row.set_text("")
        self.desc_row.set_text("")
        self.file_row.set_subtitle("No file selected")
        self.aspect_group.set_visible(False)
        self.aspect_row.set_selected(0)
        self.mode_row.set_selected(0)
        self.times_group.set_visible(False)
        self.times_row.set_value(1)
        self.next_button.set_sensitive(False)
        
        # Go back to welcome page
        self.stack.set_visible_child_name("welcome")

def main():
    app = HwPlymouther()
    return app.run()

if __name__ == "__main__":
    main()
