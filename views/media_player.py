import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import datetime as dt_module
from utils import *
from logic import *
import database
from smart_tips import generate_smart_work_tips, render_smart_work_section
import proposal
import os
import sys
import subprocess
import tempfile
import time
import shutil
import random as _rand
import database
supabase_client = database.supabase_client
STORAGE_BUCKET = database.STORAGE_BUCKET

def render(USER, USER_CONFIG):
    all_mp3s, song_options_dict, song_names_list = get_song_lists()
    conn = database.conn
    c = database.c
    st.markdown('<div id="media-player-marker"></div>', unsafe_allow_html=True)
    
    if st.session_state.music_autoswitch:
        st.html("""
        <script>
        (function() {
            let targetWin = window;
            try { if (window.parent && window.parent.document) targetWin = window.parent; } catch(e) {}
            if (targetWin._musicAutoSwitchInterval) {
                clearInterval(targetWin._musicAutoSwitchInterval);
            }
            targetWin._musicAutoSwitchInterval = setInterval(() => {
                try {
                    let audios = [];
                    try { audios = Array.from(targetWin.document.querySelectorAll('audio')); } catch(e) {}
                    try {
                        let frames = targetWin.document.querySelectorAll('iframe');
                        for (let i = 0; i < frames.length; i++) {
                            try { audios = audios.concat(Array.from(frames[i].contentWindow.document.querySelectorAll('audio'))); } catch(e) {}
                        }
                    } catch(e) {}
                    
                    for (let a of audios) {
                        const isDone = a.ended || (a.duration > 0 && a.currentTime >= a.duration - 0.3);
                        if (isDone && a.dataset.autoSwitchTriggered !== "1") {
                            a.dataset.autoSwitchTriggered = "1";
                            let b = Array.from(targetWin.document.querySelectorAll('button')).find(btn => 
                                btn.title === 'Next Song' || btn.title === 'Next' || 
                                (btn.getAttribute('aria-label') && (btn.getAttribute('aria-label') === 'Next Song' || btn.getAttribute('aria-label') === 'Next'))
                            );
                            if (b) {
                                b.click();
                            } else {
                                const url = new URL(targetWin.location.href);
                                url.searchParams.set('_auto_next', '1');
                                targetWin.location.href = url.toString();
                            }
                            return;
                        }
                        if (a.duration > 0 && a.currentTime < a.duration - 2) {
                            a.dataset.autoSwitchTriggered = "";
                        }
                    }
                } catch(e) {}
            }, 800);
        })();
        </script>
        """, unsafe_allow_javascript=True)
    
    st.title("🎵 Media Player")
    st.markdown("Your music hub — play, download, upload & manage your song library.")
    
    # ── Built-in Now Playing section (sidebar player hidden on this page) ──
    if song_names_list:
        if st.session_state.music_idx >= len(song_names_list):
            st.session_state.music_idx = 0
    
        _np_header, _np_controls = st.columns([3, 2])
        with _np_header:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                        border: 1px solid #334155;
                        border-radius: 16px; padding: 22px 26px; color: white;
                        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
                        margin-bottom: 10px;">
                <div style="font-size:11px; font-weight:600; color:#38bdf8; margin-bottom:6px;
                            letter-spacing:1.8px; text-transform:uppercase; opacity:0.9;">✨ NOW PLAYING</div>
                <div style="font-size:22px; font-weight:700; letter-spacing:0.2px; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">
                    {song_names_list[st.session_state.music_idx]}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
            _current_mp_path = song_options_dict[song_names_list[st.session_state.music_idx]]
            st.audio(get_song_url(_current_mp_path), format="audio/mp3", autoplay=st.session_state.music_playing)
    
        with _np_controls:
            def _mp_next():
                st.session_state.music_playing = True
                if st.session_state.music_shuffle:
                    idx = _rand.randint(0, len(song_names_list)-1)
                    if len(song_names_list) > 1 and idx == st.session_state.music_idx:
                        idx = (idx + 1) % len(song_names_list)
                    st.session_state.music_idx = idx
                else:
                    st.session_state.music_idx = (st.session_state.music_idx + 1) % len(song_names_list)
    
            def _mp_prev():
                st.session_state.music_playing = True
                if st.session_state.music_shuffle:
                    idx = _rand.randint(0, len(song_names_list)-1)
                    if len(song_names_list) > 1 and idx == st.session_state.music_idx:
                        idx = (idx - 1) % len(song_names_list)
                    st.session_state.music_idx = idx
                else:
                    st.session_state.music_idx = (st.session_state.music_idx - 1) % len(song_names_list)
    
            def _mp_on_sel():
                if st.session_state._mp_song_sel in song_names_list:
                    st.session_state.music_idx = song_names_list.index(st.session_state._mp_song_sel)
                    st.session_state.music_playing = True
    
            st.selectbox("Select Song", options=song_names_list,
                         index=st.session_state.music_idx,
                         key="_mp_song_sel", on_change=_mp_on_sel,
                         label_visibility="collapsed")
    
            def _mp_stop():
                st.session_state.music_playing = False
                st.session_state.music_stop_triggered = True
    
            def _mp_play():
                st.session_state.music_playing = True
                st.session_state.music_play_triggered = True
    
            _mc1, _mc2, _mc3, _mc4 = st.columns(4)
            _mc1.button("⏮️", on_click=_mp_prev, width='stretch', key="_mp_prev", help="Previous")
            if st.session_state.music_playing:
                _mc2.button("⏹️", on_click=_mp_stop, width='stretch', key="_mp_stop", help="Stop")
            else:
                _mc2.button("▶️", on_click=_mp_play, width='stretch', key="_mp_play", help="Play")
            _mc3.button("⏭️", on_click=_mp_next, width='stretch', key="_mp_next", help="Next")
            _mode_lbl = "🔀" if st.session_state.music_shuffle else "🔁"
            if _mc4.button(_mode_lbl, width='stretch', key="_mp_mode", help="Toggle Shuffle / In Order"):
                st.session_state.music_shuffle = not st.session_state.music_shuffle
                st.rerun()
    
            _mode_txt = "🔀 Shuffle" if st.session_state.music_shuffle else "🔁 In Order"
            st.markdown(f"""
                <div style="display: flex; align-items: center; justify-content: center; gap: 10px; 
                            background: #111827; padding: 8px; border-radius: 8px; border: 1px solid #374151;
                            margin-bottom: 10px;">
                    <span style="color: #9ca3af; font-size: 0.8rem;">Playback:</span>
                    <span style="color: #38bdf8; font-size: 0.9rem; font-weight: 600;">{_mode_txt}</span>
                </div>
            """, unsafe_allow_html=True)
            
            st.session_state.music_autoswitch = st.checkbox(
                "⏩ Auto-switch at end",
                value=st.session_state.music_autoswitch,
                key="music_auto_chk"
            )
    
        # --- JS: actually stop or play audio on Media Player page ---
        if st.session_state.get("music_stop_triggered"):
            st.session_state.music_stop_triggered = False
            st.html("""
            <script>
            (function stopAllAudio() {
                var attempts = 0;
                function tryStop() {
                    try {
                        var audios = window.parent.document.querySelectorAll('audio');
                        audios.forEach(function(a) {
                            a.pause();
                            a.currentTime = 0;
                        });
                    } catch(e) {}
                    if (++attempts < 5) setTimeout(tryStop, 200);
                }
                tryStop();
            })();
            </script>
            """, unsafe_allow_javascript=True)
        elif st.session_state.get("music_play_triggered"):
            st.session_state.music_play_triggered = False
            st.html("""
            <script>
            (function playAudio() {
                var attempts = 0;
                function tryPlay() {
                    try {
                        var audio = window.parent.document.querySelector('audio');
                        if (audio) { audio.play(); }
                    } catch(e) {}
                    if (++attempts < 5) setTimeout(tryPlay, 200);
                }
                tryPlay();
            })();
            </script>
            """, unsafe_allow_javascript=True)
    
        # Autoswitch JS was moved to top of block for persistence
    else:
        st.info("🎵 No audio files found. Try downloading or uploading one above!")
    
    st.divider()
    
    tab_yt, tab_upload, tab_manage = st.tabs(["🔗 YouTube Download", "📤 Upload MP3", "📋 Manage Songs"])
    
    with tab_yt:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                    border: 1px solid #38bdf8; border-radius: 14px;
                    padding: 18px 20px; margin-bottom: 18px;">
            <div style="font-size:16px; font-weight:600; color:#38bdf8; margin-bottom:8px;">
                🔗 YouTube Downloader
            </div>
            <div style="font-size:13px; color:#94a3b8;">
                Paste a link below to fetch new tracks. They will appear in your library automatically.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        yt_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
        custom_name = st.text_input("Custom filename (optional)", placeholder="Leave blank to use video title")
        
        # --- Advanced Settings for bypassing blocks ---
        with st.expander("🛠️ Advanced Settings (Bypass 403 Forbidden)"):
            st.markdown("""
            YouTube often blocks requests from cloud servers. If you get a **403 Forbidden** error:
            1. Use a **Cookies** file (Netscape format). Use 'Get cookies.txt' extension.
            2. Or try a different video.
            """)
            cookie_text = st.text_area("Paste Cookies Content", height=100, help="Paste the content of your cookies.txt here.")
            force_update = st.checkbox("Force update yt-dlp & ffmpeg before download", value=False)
            col_client, col_mobile = st.columns(2)
            with col_client:
                # Changed default to android (index 1) as it often handles challenges better
                player_client = st.selectbox("Player Client", ["android", "ios", "web", "mweb", "tv"], index=0, help="Changing this can help if a video is blocked or signature fails.")
            with col_mobile:
                use_mobile_client = st.checkbox("Use Advanced Client Strategy", value=True)
            
            st.info("💡 **Tip:** If you see 'n challenge solving failed', ensure you have **Node.js** installed on your server/computer. I've added it to `packages.txt` for Streamlit Cloud.")
    
        if st.button("⬇️ Download as MP3", type="primary", width='stretch'):
            if yt_url.strip():
                # Update only if forced or if it's the first time
                if force_update:
                    with st.spinner("🎵 Updating downloader tools..."):
                        try:
                            subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp", "static-ffmpeg"], check=True, capture_output=True)
                        except Exception as e:
                            st.warning(f"Update failed: {e}")
                
                # 1. Try to find ffmpeg (System first, then static-ffmpeg)
                ffmpeg_location = shutil.which("ffmpeg")
                if not ffmpeg_location:
                    try:
                        import static_ffmpeg
                        pkg_dir = os.path.dirname(static_ffmpeg.__file__)
                        potential_bins = [
                            os.path.join(pkg_dir, "bin", "win32"),
                            os.path.join(pkg_dir, "bin"),
                            os.path.join(pkg_dir, "static_ffmpeg", "bin", "win32")
                        ]
                        ffmpeg_exe = "ffmpeg.exe" if os.name == 'nt' else "ffmpeg"
                        for pb in potential_bins:
                            target_exe = "ffmpeg.exe" if os.name == 'nt' else "ffmpeg"
                            target = os.path.join(pb, target_exe)
                            if os.path.exists(target):
                                ffmpeg_location = target
                                break
                    except:
                        pass
                
                # Ultimate fallback for Streamlit Cloud (Linux) if static_ffmpeg doesn't work out of the box
                if not ffmpeg_location and os.name != 'nt':
                    if os.path.exists("/usr/bin/ffmpeg"):
                        ffmpeg_location = "/usr/bin/ffmpeg"
    
                # 2. Check for Node.js (required for 'n challenge' signature decryption)
                # Streamlit Cloud usually has nodejs if added to packages.txt
                node_available = shutil.which("node") or shutil.which("nodejs")
                if not node_available:
                    with st.spinner("🔧 Providing JavaScript runtime for bypass..."):
                        try:
                            # Try nodejs-bin as fallback
                            subprocess.run([sys.executable, "-m", "pip", "install", "nodejs-bin"], capture_output=True)
                            import nodejs_bin
                            node_dir = os.path.dirname(nodejs_bin.__file__)
                            # Exhaustive search for the node binary
                            for sub in ["bin", "node_bin", "scripts", "Scripts", ""]:
                                bp = os.path.abspath(os.path.join(node_dir, sub))
                                for exe in ["node", "node.exe", "nodejs"]:
                                    if os.path.exists(os.path.join(bp, exe)):
                                        if bp not in os.environ["PATH"]:
                                            os.environ["PATH"] = bp + os.pathsep + os.environ["PATH"]
                                        node_available = os.path.join(bp, exe)
                                        break
                                if node_available: break
                        except: pass
    
                with st.spinner("🎵 Downloading and converting to MP3..."):
                    try:
                        output_template = f"{custom_name.strip()}.%(ext)s" if custom_name.strip() else "%(title)s.%(ext)s"
                        
                        # Create temporary cookie file if provided
                        cookie_file_path = None
                        final_cookie_text = cookie_text.strip()
                        
                        # Fallback to Streamlit Secrets for cookies if available
                        if not final_cookie_text and "YOUTUBE_COOKIES" in st.secrets:
                            final_cookie_text = st.secrets["YOUTUBE_COOKIES"]
                            
                        if final_cookie_text:
                            fd, cookie_file_path = tempfile.mkstemp(suffix=".txt")
                            with os.fdopen(fd, 'w') as tmp:
                                tmp.write(final_cookie_text)
    
                        # Build the command
                        cmd = [
                            sys.executable, "-m", "yt_dlp",
                            "-x",
                            "--audio-format", "mp3",
                            "--audio-quality", "192K",
                            "-o", output_template,
                            "--no-playlist",
                            "--no-check-certificate",
                            "--prefer-free-formats",
                            "--format", "bestaudio/best",
                            "--add-header", "Accept-Language:en-US,en;q=0.9"
                        ]
                        
                        # Add cookies if available
                        if cookie_file_path:
                            cmd.extend(["--cookies", cookie_file_path])
                        elif os.name == 'nt':
                            try: cmd.extend(["--cookies-from-browser", "chrome+edge"])
                            except: pass
                            
                        # Strategy helper
                        def get_cmd_for_strat(base_cmd, strat):
                            c = base_cmd.copy()
                            # ios and android_music are best for bypassing n-challenge
                            c.extend(["--extractor-args", f"youtube:player_client={strat}"])
                            if "ios" in strat:
                                c.extend(["--user-agent", "com.google.ios.youtube/19.12.3 (iPhone16,2; U; CPU iOS 17_4_1 like Mac OS X; en_US) gzip"])
                            elif "android" in strat:
                                c.extend(["--user-agent", "com.google.android.youtube/19.12.39 (Linux; U; Android 14; en_US) gzip"])
                            elif "tv" in strat:
                                c.extend(["--user-agent", "Mozilla/5.0 (Chromecast; Google TV) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"])
                            
                            # Add referer to look less like a direct bot request
                            c.extend(["--referer", "https://www.youtube.com/"])
                            return c
    
                        # Set initial strategy to Android VR (currently the most resilient against n-challenge without JS)
                        # We also try android_music and ios.
                        initial_strat = "android,android_music,ios"
                        full_cmd = get_cmd_for_strat(cmd, initial_strat)
                        
                        # Add these to completely bypass the need for a JS runtime in yt-dlp
                        full_cmd.extend(["--extractor-args", "youtube:player_skip=js;youtube:player_client=android"])
                        
                        # Set ffmpeg location if we found a non-system one
                        if ffmpeg_location and not shutil.which("ffmpeg"):
                            full_cmd.extend(["--ffmpeg-location", ffmpeg_location])
                        
                        full_cmd.extend([
                            "--restrict-filenames" if not custom_name.strip() else "--no-restrict-filenames",
                            yt_url.strip()
                        ])
                        
                        # --- TRY 1 ---
                        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=300, env=os.environ)
                        
                        # --- AUTOMATIC RETRY IF BLOCKED OR SIGNATURE FAILS ---
                        is_blocked = "403" in result.stderr or "forbidden" in result.stderr.lower()
                        is_challenge = "signature" in result.stderr.lower() or "n challenge" in result.stderr.lower()
                        is_bot = "confirm you're not a bot" in result.stderr.lower()
                        
                        if result.returncode != 0 and (is_blocked or is_challenge or is_bot):
                            st.info("🔄 Issue detected. Attempting deep bypass and recursive retries...")
                            try:
                                # Update and clear cache
                                subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"], capture_output=True)
                                subprocess.run([sys.executable, "-m", "yt_dlp", "--rm-cache-dir"], capture_output=True)
                            except: pass
                                
                            # Expanded Strategy Pool
                            strategies = [
                                "ios", "android_music", "android", "web,tv", 
                                "mweb,ios", "web_creator", "tv,android", "mweb"
                            ]
                            
                            for strat in strategies:
                                st.caption(f"Recursive retry attempt using strategy: {strat}...")
                                retry_cmd = get_cmd_for_strat(cmd, strat)
                                if ffmpeg_location and not shutil.which("ffmpeg"):
                                    retry_cmd.extend(["--ffmpeg-location", ffmpeg_location])
                                
                                # Add deep bypass flags
                                retry_cmd.extend(["--geo-bypass", "--no-check-certificate"])
                                retry_cmd.extend([
                                    "--restrict-filenames" if not custom_name.strip() else "--no-restrict-filenames",
                                    yt_url.strip()
                                ])
                                
                                result = subprocess.run(retry_cmd, capture_output=True, text=True, timeout=300, env=os.environ)
                                if result.returncode == 0:
                                    st.success(f"✅ Success! Bypass found with {strat} strategy.")
                                    break
                                elif "429" in result.stderr:
                                    st.warning(f"⚠️ Rate limited on {strat}. Pausing...")
                                    time.sleep(2)
                        
                        # Cleanup cookie file and any leftover webm/m4a files
                        if cookie_file_path and os.path.exists(cookie_file_path):
                            try: os.remove(cookie_file_path)
                            except: pass
                        
                        # Only cleanup temp files, not supported audio
                        for f in os.listdir("."):
                            if f.endswith(".part") or f.endswith(".ytdl"):
                                try: os.remove(f)
                                except: pass
                        
                        if result.returncode == 0:
                            # Upload to Supabase if available
                            downloaded_file = None
                            # Find all matching mp3s and pick the most recent one
                            matches = []
                            _audio_exts = (".mp3", ".m4a", ".webm", ".wav", ".ogg")
                            for f in os.listdir("."):
                                if f.lower().endswith(_audio_exts):
                                    if not custom_name.strip() or custom_name.strip() in f:
                                        matches.append(f)
                            
                            if matches:
                                matches.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                                downloaded_file = matches[0]
                             
                            if downloaded_file and supabase_client:
                                with st.spinner("☁️ Uploading to Supabase Storage..."):
                                    try:
                                        with open(downloaded_file, "rb") as f:
                                            supabase_client.storage.from_(STORAGE_BUCKET).upload(
                                                path=downloaded_file,
                                                file=f,
                                                file_options={"content-type": "audio/mpeg"}
                                            )
                                        os.remove(downloaded_file) # Clean up local
                                        st.success("✅ Uploaded to Supabase!")
                                    except Exception as upload_err:
                                        st.warning(f"Local download ok, but Supabase upload failed: {upload_err}")
    
                            st.success("✅ Download complete! Adding to library...")
                            st.balloons()
                            import time
                            time.sleep(2)
                            st.rerun()
                        else:
                            err_msg = result.stderr
                            if "403: Forbidden" in err_msg:
                                st.error("❌ **YouTube blocked the request (403 Forbidden).**\n\nYouTube has flagged this server's IP. To fix this:\n1. Expand 'Advanced Settings' above.\n2. Paste your **YouTube Cookies** (Netscape format).\n3. Try again.\n\n*Changing the 'Player Client' in Advanced Settings also helps.*")
                            elif "n challenge" in err_msg.lower() or "signature" in err_msg.lower():
                                st.error("❌ **Signature Challenge Failed even after automatic retries.**\n\nYouTube is using a new security measure that requires a JavaScript runtime. I've attempted to automatically install a Node.js runtime and retry with different strategies, but it still failed. To fix this definitively:\n1. Expand **Advanced Settings** above.\n2. Paste your **YouTube Cookies** (Netscape format).\n3. Try again. This bypasses the signature challenge entirely.")
                            elif "Requested format is not available" in err_msg:
                                st.error("❌ **Format not available.**\n\nYouTube is hiding the audio formats for this video from this server. Try using **Cookies** or changing the **Player Client** to **Android**.")
                            elif "ffmpeg" in err_msg.lower():
                                st.error("❌ **ffmpeg not found.**\n\nConversion to MP3 failed. I've attempted to install it. Please try again.")
                            else:
                                st.error(f"Download failed:\n```\n{err_msg[-500:]}\n```")
                    except subprocess.TimeoutExpired:
                        st.error("⏱️ Download timed out (5 min limit). Try a shorter video.")
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.warning("Please enter a YouTube URL.")
    
    with tab_upload:
        st.markdown("### 📤 Upload an audio file directly")
        uploaded_file = st.file_uploader("Choose an audio file", type=["mp3", "m4a", "webm", "wav", "ogg"])
        if uploaded_file is not None:
            save_name = st.text_input("Save as (filename)", value=uploaded_file.name, key="upload_save_name")
            # Auto-append .mp3 only if no supported extension is present
            _audio_exts = (".mp3", ".m4a", ".webm", ".wav", ".ogg")
            if not any(save_name.lower().endswith(ext) for ext in _audio_exts):
                save_name += ".mp3"
            if st.button("💾 Save Song", key="save_upload_btn"):
                if supabase_client:
                    with st.spinner("☁️ Uploading to Supabase..."):
                        try:
                            supabase_client.storage.from_(STORAGE_BUCKET).upload(
                                path=save_name,
                                file=uploaded_file.getbuffer().tobytes(),
                                file_options={"content-type": "audio/mpeg"}
                            )
                            st.success(f"✅ Uploaded **{save_name}** to Supabase!")
                        except Exception as e:
                            st.error(f"Supabase upload failed: {e}")
                else:
                    with open(save_name, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.success(f"✅ Saved locally as **{save_name}**")
                
                st.balloons()
                import time; time.sleep(1)
                st.rerun()
    
    with tab_manage:
        st.markdown("### 📋 Current Song Library")
        
        # Add refresh button in management tab too
        _refresh_col, _debug_col = st.columns([1, 1])
        with _refresh_col:
            if st.button("🔄 Rescan Library", key="rescan_btn", width='stretch'):
                st.session_state._refresh_music = True
                st.rerun()
        
        with _debug_col:
            with st.expander("🛠️ Library Debug"):
                st.write(f"**CWD:** `{os.getcwd()}`")
                st.write(f"**Total Songs Found:** {len(all_mp3s)}")
                st.write("**Local Paths Scanned:**")
                st.json(all_mp3s)
            
        current_mp3s = all_mp3s # Use the already computed list
        if not current_mp3s:
            st.info("No songs found.")
        else:
            st.caption(f"**{len(current_mp3s)}** songs in library")
            for mp3 in sorted(current_mp3s):
                # Try to get size from supabase or local
                try:
                    if supabase_client:
                        # Listing already gave us some info but let's keep it simple
                        file_size_mb = 0 # Difficult to get size for each without extra calls
                    else:
                        file_size_mb = os.path.getsize(mp3) / (1024 * 1024)
                except:
                    file_size_mb = 0
    
                mc1, mc2, mc3 = st.columns([3, 1, 1])
                mc1.markdown(f"🎵 **{clean_song_name(mp3)}**")
                if file_size_mb > 0:
                    mc2.caption(f"{file_size_mb:.1f} MB")
                else:
                    mc2.caption("Cloud")
                
                if mc3.button("🗑️", key=f"del_song_{mp3}", help=f"Delete {mp3}"):
                    st.session_state[f"confirm_del_song_{mp3}"] = True
                
                if st.session_state.get(f"confirm_del_song_{mp3}", False):
                    st.warning(f"⚠️ Delete **{mp3}**? This cannot be undone.")
                    yc, nc = st.columns(2)
                    if yc.button("✅ Yes, Delete", key=f"yes_del_song_{mp3}"):
                        try:
                            if supabase_client:
                                supabase_client.storage.from_(STORAGE_BUCKET).remove([mp3])
                            if os.path.exists(mp3):
                                os.remove(mp3)
                            st.toast(f"🗑️ '{mp3}' deleted.", icon="🗑️")
                            st.session_state[f"confirm_del_song_{mp3}"] = False
                            import time; time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting file: {e}")
                    if nc.button("❌ No, Keep", key=f"no_del_song_{mp3}"):
                        st.session_state[f"confirm_del_song_{mp3}"] = False
                        st.rerun()
    st.stop()
    
