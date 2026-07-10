' EntryBox launcher (Windows).
' Ensures the local server is running, then opens EntryBox in an app window
' (chromeless, own taskbar icon). Safe to run repeatedly: if the server is
' already up it just opens the window.
Option Explicit

Dim sh, fso, repo, i
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Script lives at <repo>\scripts\windows\ ; walk two folders up.
repo = fso.GetParentFolderName(fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName)))

Function Healthy()
  Dim http
  Healthy = False
  On Error Resume Next
  Set http = CreateObject("MSXML2.XMLHTTP")
  http.Open "GET", "http://127.0.0.1:3859/health", False
  http.Send
  If Err.Number = 0 Then
    If http.Status = 200 Then Healthy = True
  End If
  On Error GoTo 0
End Function

If Not Healthy() Then
  Dim py
  ' python.exe with a hidden window, NOT pythonw.exe: pythonw has no
  ' stdout/stderr and uvicorn's logging dies instantly without them.
  py = repo & "\.venv\Scripts\python.exe"
  sh.CurrentDirectory = repo
  If fso.FileExists(py) Then
    sh.Run """" & py & """ -m uvicorn app.main:app --host 127.0.0.1 --port 3859", 0, False
  Else
    ' First run: no venv yet. run.bat bootstraps visibly so errors are seen.
    sh.Run """" & repo & "\run.bat""", 1, False
  End If
  For i = 1 To 60
    If Healthy() Then Exit For
    WScript.Sleep 500
  Next
End If

' Prefer an app window (Edge ships with Windows 11, Chrome as fallback);
' otherwise the default browser gets a normal tab.
Dim edge, chrome
edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
If Not fso.FileExists(edge) Then edge = "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"

If fso.FileExists(edge) Then
  sh.Run """" & edge & """ --app=http://localhost:3859", 1, False
ElseIf fso.FileExists(chrome) Then
  sh.Run """" & chrome & """ --app=http://localhost:3859", 1, False
Else
  sh.Run "http://localhost:3859", 1, False
End If
