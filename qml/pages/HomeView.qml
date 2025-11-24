import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import Qt.labs.platform 1.1 // For FolderDialog

Item {
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        // Header
        Text {
            text: "CLASSIC Dashboard"
            font.pixelSize: 28
            font.bold: true
            color: "white"
        }

        // Staging Mods Folder
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 5
            Label { 
                text: "Staging Mods Folder" 
                color: "#cccccc"
                font.bold: true
            }
            RowLayout {
                Layout.fillWidth: true
                TextField {
                    id: modsPathField
                    Layout.fillWidth: true
                    placeholderText: "Optional: Select your mod staging folder (e.g., MO2/mods)"
                    text: backend.stagingModsPath
                    color: "white"
                    background: Rectangle {
                        color: "#333333"
                        border.color: "#555"
                        radius: 4
                    }
                    onEditingFinished: backend.stagingModsPath = text
                }
                                    Button {
                                        text: "Browse..."
                                        onClicked: modsDialog.open()
                                        background: Rectangle {
                                            color: parent.hovered ? window.buttonHoverColor : window.buttonColor
                                            radius: 4
                                        }
                                        contentItem: Text {
                                            text: parent.text
                                            color: "white"
                                            horizontalAlignment: Text.AlignHCenter
                                            verticalAlignment: Text.AlignVCenter
                                        }
                                    }                FolderDialog {
                    id: modsDialog
                    title: "Select Staging Mods Folder"
                    onAccepted: {
                        // Path comes as URL, need to strip file:///
                        var path = currentFolder.toString()
                        if (Qt.platform.os === "windows") {
                            path = path.replace("file:///", "")
                        } else {
                            path = path.replace("file://", "")
                        }
                        backend.stagingModsPath = decodeURIComponent(path)
                    }
                }
            }
        }

        // Custom Scan Folder
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 5
            Label { 
                text: "Custom Scan Folder" 
                color: "#cccccc"
                font.bold: true
            }
            RowLayout {
                Layout.fillWidth: true
                TextField {
                    id: scanPathField
                    Layout.fillWidth: true
                    placeholderText: "Optional: Select a supplementary custom folder with crash logs"
                    text: backend.customScanPath
                    color: "white"
                    background: Rectangle {
                        color: "#333333"
                        border.color: "#555"
                        radius: 4
                    }
                    onEditingFinished: backend.customScanPath = text
                }
                Button {
                    text: "Browse..."
                    onClicked: scanDialog.open()
                    background: Rectangle {
                        color: parent.hovered ? window.buttonHoverColor : window.buttonColor
                        radius: 4
                    }
                    contentItem: Text {
                        text: parent.text
                        color: "white"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                FolderDialog {
                    id: scanDialog
                    title: "Select Custom Scan Folder"
                    onAccepted: {
                        var path = currentFolder.toString()
                        if (Qt.platform.os === "windows") {
                            path = path.replace("file:///", "")
                        } else {
                            path = path.replace("file://", "")
                        }
                        backend.customScanPath = decodeURIComponent(path)
                    }
                }
            }
        }
        
        // Pastebin
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 5
            Label { 
                text: "Pastebin Fetch" 
                color: "#cccccc"
                font.bold: true
            }
            RowLayout {
                Layout.fillWidth: true
                TextField {
                    id: pastebinField
                    Layout.fillWidth: true
                    placeholderText: "Enter Pastebin URL or ID"
                    color: "white"
                    background: Rectangle {
                        color: "#333333"
                        border.color: "#555"
                        radius: 4
                    }
                }
                Button {
                    text: "Fetch Log"
                    onClicked: {
                        if (pastebinField.text.length > 0) {
                            backend.fetchPastebin(pastebinField.text)
                            pastebinField.text = ""
                        }
                    }
                    background: Rectangle {
                        color: parent.hovered ? window.buttonHoverColor : window.buttonColor
                        radius: 4
                    }
                    contentItem: Text {
                        text: parent.text
                        color: "white"
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }

        Item { Layout.fillHeight: true } // Spacer

        // Main Actions
        RowLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignHCenter
            spacing: 20

            Button {
                text: "SCAN CRASH LOGS"
                Layout.fillWidth: true
                Layout.preferredHeight: 60
                
                background: Rectangle {
                    color: parent.hovered ? "#555" : "#e1e1e1"
                    radius: 8
                }
                contentItem: Text {
                    text: parent.text
                    color: "black"
                    font.bold: true
                    font.pixelSize: 18
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: backend.scanCrashLogs()
            }

            Button {
                text: "SCAN GAME FILES"
                Layout.fillWidth: true
                Layout.preferredHeight: 60

                background: Rectangle {
                    color: parent.hovered ? "#555" : "#e1e1e1"
                    radius: 8
                }
                contentItem: Text {
                    text: parent.text
                    color: "black"
                    font.bold: true
                    font.pixelSize: 18
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: backend.scanGameFiles()
            }
        }

        // Bottom Actions
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            
            Button {
                text: backend.papyrusMonitoring ? "STOP PAPYRUS MONITOR" : "START PAPYRUS MONITOR"
                Layout.fillWidth: true
                
                background: Rectangle {
                    color: parent.hovered ? (backend.papyrusMonitoring ? "#c42b1c" : "#14a714") : (backend.papyrusMonitoring ? "#e81123" : "#107c10")
                    radius: 4
                }
                contentItem: Text {
                    text: parent.text
                    color: "white"
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: backend.togglePapyrus()
            }
            
            Button {
                text: "OPEN CRASH LOGS"
                Layout.fillWidth: true
                background: Rectangle {
                    color: parent.hovered ? window.buttonHoverColor : window.buttonColor
                    radius: 4
                }
                contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                onClicked: backend.openCrashLogsFolder()
            }
        }
        
        // Status / Notifications
        Text {
            id: statusText
            text: "Ready"
            color: "#888"
            Layout.alignment: Qt.AlignHCenter
        }
    }
    
    Connections {
        target: backend
        function onScanFinished() {
            statusText.text = "Scan Finished"
        }
    }
}
