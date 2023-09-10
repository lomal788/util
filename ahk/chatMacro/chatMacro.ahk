#SingleInstance, Force
SendMode Input
SetWorkingDir, %A_ScriptDir%
Menu,Tray,NoStandard
Menu,Tray,Add,닫기,GuiClose

version=1.0
;gui,+alwaysontop
gui,show,x0 y0 w900 h0,채팅매크로 version : %version%. 종료(F12)
time:=300
SetTitleMatchMode,3

FileEncoding, UTF-8

IniRead, configVer, config.ini, CONFIG, version
;IniRead, text1, config.ini, CHAT, text1
FileRead, text1, chat1.txt
FileRead, text2, chat2.txt
FileRead, text3, chat3.txt
FileRead, text4, chat4.txt
FileRead, text5, chat5.txt
FileRead, text6, chat6.txt
FileRead, text7, chat7.txt
FileRead, text8, chat8.txt
FileRead, text9, chat9.txt
FileRead, text0, chat10.txt
/*

IniRead, text2, config.ini, CHAT, text2
IniRead, text3, config.ini, CHAT, text3
IniRead, text4, config.ini, CHAT, text4
IniRead, text5, config.ini, CHAT, text5
IniRead, text6, config.ini, CHAT, text6
IniRead, text7, config.ini, CHAT, text7
IniRead, text8, config.ini, CHAT, text8
IniRead, text19, config.ini, CHAT, text9
IniRead, text10, config.ini, CHAT, text10


FileDelete, emote2.txt
Gui, Submit, Nohide
FileAppend, %Emote1%`n%Emote2%`n%Emote3%`n%Emote4%`n%Emote5%`n, emote2.txt

Apressed = F2
Apressed::
핫키지정
return

*/


if(configVer <> version ){
    MsgBox, 버전을 확인해주세요.
    Exitapp
}

if (!FileExist("chat1.txt") OR
    !FileExist("chat2.txt") OR
    !FileExist("chat3.txt") OR
    !FileExist("chat4.txt") OR
    !FileExist("chat5.txt") OR
    !FileExist("chat6.txt") OR
    !FileExist("chat7.txt") OR
    !FileExist("chat8.txt") OR
    !FileExist("chat9.txt") OR
    !FileExist("chat10.txt") ) {
    FileDelete, chat1.txt
    FileDelete, chat2.txt
    FileDelete, chat3.txt
    FileDelete, chat4.txt
    FileDelete, chat5.txt
    FileDelete, chat6.txt
    FileDelete, chat7.txt
    FileDelete, chat8.txt
    FileDelete, chat9.txt
    FileDelete, chat10.txt

    FileAppend, Alt 1 입력시 문구 노출됩니다., chat1.txt
    FileAppend, Alt 2 입력시 문구 노출됩니다., chat2.txt
    FileAppend, Alt 3 입력시 문구 노출됩니다., chat3.txt
    FileAppend, Alt 4 입력시 문구 노출됩니다., chat4.txt
    FileAppend, Alt 5 입력시 문구 노출됩니다., chat5.txt
    FileAppend, Alt 6 입력시 문구 노출됩니다., chat6.txt
    FileAppend, Alt 7 입력시 문구 노출됩니다., chat7.txt
    FileAppend, Alt 8 입력시 문구 노출됩니다., chat8.txt
    FileAppend, Alt 9 입력시 문구 노출됩니다., chat9.txt
    FileAppend, Alt 10 입력시 문구 노출됩니다., chat10.txt

    MsgBox, 채팅매크로 파일이없으므로 재설정합니다. chat.txt파일 설정후 다시 실행해주세요.
    Exitapp
}

#NoEnv

sendText(text){
    Clipboard = %text%
    send,^v
    return    
}

sendEvent(index) {
    sendText(text%index%)
    return
}

i:= 0
keyPressed= !0
Loop, 10{
    fn := Func("sendEvent").Bind(i)
    Hotkey, %keyPressed%, % fn
    i+=1
    keyPressed=!%i%
}

F12::
MsgBox, 프로그램을 종료합니다.
Exitapp

GuiClose:
ExitApp
Return

