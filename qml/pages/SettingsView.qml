import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import Qt.labs.platform 1.1
import "../components"

Item {
    ScrollView {
        anchors.fill: parent
        contentWidth: parent.width
        clip: true

        ColumnLayout {
            width: parent.width - 40
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 20
            
            Text {
                text: "Settings"
                font.pixelSize: 24
                font.bold: true
                color: "white"
            }

            // General
            GroupBox {
                title: "General"
                Layout.fillWidth: true
                background: Rectangle { color: "transparent"; border.color: "#555"; radius: 4 }
                label: Label { text: parent.title; color: "white"; font.bold: true; padding: 5 }

                ColumnLayout {
                    anchors.fill: parent
                    ToggleSwitch {
                        text: "Audio Notifications"
                        checked: backend.audioNotifications
                        onToggled: backend.audioNotifications = checked
                    }
                    ToggleSwitch {
                        text: "VR Mode"
                        checked: backend.vrMode
                        onToggled: backend.vrMode = checked
                    }
                }
            }

            // Scanning
            GroupBox {
                title: "Scanning"
                Layout.fillWidth: true
                background: Rectangle { color: "transparent"; border.color: "#555"; radius: 4 }
                label: Label { text: parent.title; color: "white"; font.bold: true; padding: 5 }

                ColumnLayout {
                    anchors.fill: parent
                    ToggleSwitch {
                        text: "FCX Mode (Extended Checks)"
                        checked: backend.fcxMode
                        onToggled: backend.fcxMode = checked
                    }
                    ToggleSwitch {
                        text: "Simplify Logs"
                        checked: backend.simplifyLogs
                        onToggled: backend.simplifyLogs = checked
                    }
                    ToggleSwitch {
                        text: "Show FormID Values (Slower)"
                        checked: backend.showFidValues
                        onToggled: backend.showFidValues = checked
                    }
                    ToggleSwitch {
                        text: "Move Unsolved Logs"
                        checked: backend.moveInvalidLogs
                        onToggled: backend.moveInvalidLogs = checked
                    }
                }
            }

            // Paths
            GroupBox {
                title: "Paths"
                Layout.fillWidth: true
                background: Rectangle { color: "transparent"; border.color: "#555"; radius: 4 }
                label: Label { text: parent.title; color: "white"; font.bold: true; padding: 5 }

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10
                    
                    Label { text: "INI Folder Path (Documents/My Games/Fallout4)"; color: "#ccc" }
                    RowLayout {
                        Layout.fillWidth: true
                        TextField {
                            id: iniPathField
                            Layout.fillWidth: true
                            text: backend.iniPath
                            placeholderText: "Leave empty to auto-detect"
                            color: "white"
                            background: Rectangle { color: "#333"; border.color: "#555"; radius: 4 }
                            onEditingFinished: backend.iniPath = text
                        }
                        Button {
                            text: "Browse..."
                            onClicked: iniDialog.open()
                            background: Rectangle {
                                color: parent.hovered ? window.buttonHoverColor : window.buttonColor
                                radius: 4
                            }
                            contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        }
                        FolderDialog {
                            id: iniDialog
                            title: "Select INI Folder"
                            onAccepted: {
                                var path = currentFolder.toString()
                                if (Qt.platform.os === "windows") {
                                    path = path.replace("file:///", "")
                                } else {
                                    path = path.replace("file://", "")
                                }
                                backend.iniPath = decodeURIComponent(path)
                            }
                        }
                    }
                }
            }

            // Updates
            GroupBox {
                title: "Updates"
                Layout.fillWidth: true
                background: Rectangle { color: "transparent"; border.color: "#555"; radius: 4 }
                label: Label { text: parent.title; color: "white"; font.bold: true; padding: 5 }

                ColumnLayout {
                    anchors.fill: parent
                    ToggleSwitch {
                        text: "Check for Updates on Startup"
                        checked: backend.updateCheck
                        onToggled: backend.updateCheck = checked
                    }
                }
            }
        }
    }
}
