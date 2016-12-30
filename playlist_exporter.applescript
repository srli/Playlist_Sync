try
	tell application "Finder"
		delete (every item of folder (((path to home folder) as text) & "Scripts:playlist_sync:playlists") whose name ends with ".xml")
	end tell
on error errMsg number errNum
	display dialog "Error " & errNum & return & return & errMsg buttons {"Cancel"} default button 1
end try

tell application "iTunes"
	set playlist_names to (get name of playlists)
	set cleaned_pl to items 13 thru end of playlist_names
end tell

repeat with pl in cleaned_pl
	if pl begins with "+" then
		tell application "iTunes" to set pl_names to name of tracks of playlist pl
		tell application "iTunes" to set pl_durations to time of tracks of playlist pl
		
		set song_info to {}
		repeat with n from 1 to count of pl_names
			set song_info to song_info & ((item n of pl_names) & ":::" & (item n of pl_durations))
		end repeat
		set {text item delimiters, TID} to {"+++", text item delimiters}
		set {text item delimiters, song_info_str} to {TID, song_info as text}
		
		set xml_file to "/Users/sophie/Scripts/playlist_sync/playlists/" & pl & ".xml"
		
		try
			open for access xml_file with write permission
			set fileRef to result
			
			write song_info_str to fileRef
			close access fileRef
		on error errMsg number errNum
			try
				close access fileRef
			end try
			
			display dialog "Error " & errNum & return & return & errMsg buttons {"Cancel"} default button 1
		end try
	end if
end repeat