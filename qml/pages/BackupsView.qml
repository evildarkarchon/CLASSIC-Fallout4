import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        Text {
            text: "Game File Backups"
            font.pixelSize: 24
            font.bold: true
            color: "white"
            Layout.alignment: Qt.AlignHCenter
        }
        
        Label {
            text: "BACKUP: Copy files from game folder to CLASSIC Backup.\nRESTORE: Restore files from CLASSIC Backup to game folder.\nREMOVE: Delete files from game folder (backups remain)."
            color: "#ccc"
            Layout.alignment: Qt.AlignHCenter
            horizontalAlignment: Text.AlignHCenter
        }

        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 15

            model: ["XSE", "RESHADE", "VULKAN", "ENB"]

            delegate: ColumnLayout {
                width: ListView.view.width
                spacing: 10

                Text {
                    text: modelData
                    color: "white"
                    font.bold: true
                    font.pixelSize: 18
                    Layout.alignment: Qt.AlignHCenter
                }

                RowLayout {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 10

                    Button {
                        text: "BACKUP"
                        onClicked: backend.backupOperation(modelData, "BACKUP")
                        background: Rectangle {
                            color: parent.hovered ? window.buttonHoverColor : window.buttonColor
                            radius: 4
                            border.color: "#555"
                        }
                        contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    }
                    Button {
                        text: "RESTORE"
                        onClicked: backend.backupOperation(modelData, "RESTORE")
                        background: Rectangle {
                            color: parent.hovered ? window.buttonHoverColor : window.buttonColor
                            radius: 4
                            border.color: "#555"
                        }
                        contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    }
                    Button {
                        text: "REMOVE"
                        onClicked: backend.backupOperation(modelData, "REMOVE")
                        background: Rectangle {
                            color: parent.hovered ? window.buttonHoverColor : window.buttonColor
                            radius: 4
                            border.color: "#555"
                        }
                        contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    }
                }
                
                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: "#444"
                }
            }
        }
        
        Button {
            text: "OPEN CLASSIC BACKUPS FOLDER"
            Layout.alignment: Qt.AlignHCenter
            onClicked: backend.openBackupFolder()
            background: Rectangle {
                color: parent.hovered ? window.buttonHoverColor : window.buttonColor
                radius: 4
            }
            contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        }
    }
}
