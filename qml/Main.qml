import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15
import "pages"

ApplicationWindow {
    id: window
    width: 1000
    height: 700
    visible: true
    title: "Crash Log Auto Scanner & Setup Integrity Checker | " + backend.version
    color: "#1e1e1e"

    property color accentColor: "#0078d4"
    property color backgroundColor: "#1e1e1e"
    property color sidebarColor: "#252526"
    property color textColor: "#ffffff"
    property color buttonColor: "#333333"
    property color buttonHoverColor: "#555555"

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Sidebar
        Rectangle {
            Layout.preferredWidth: 250
            Layout.fillHeight: true
            color: sidebarColor

            ColumnLayout {
                anchors.fill: parent
                spacing: 5
                anchors.margins: 10

                Text {
                    text: "CLASSIC"
                    color: textColor
                    font.pixelSize: 24
                    font.bold: true
                    Layout.alignment: Qt.AlignHCenter
                    Layout.bottomMargin: 20
                }

                // Navigation Buttons
                Repeater {
                    model: ["Home", "Articles", "Backups", "Results", "Settings"]
                    
                    Button {
                        text: modelData
                        Layout.fillWidth: true
                        height: 40
                        
                        background: Rectangle {
                            color: parent.checked ? accentColor : (parent.hovered ? buttonHoverColor : "transparent")
                            radius: 4
                        }
                        
                        contentItem: Text {
                            text: parent.text
                            color: textColor
                            font.pixelSize: 16
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: 15
                        }

                        checkable: true
                        autoExclusive: true
                        checked: index === 0
                        
                        onClicked: {
                            viewStack.currentIndex = index
                        }
                    }
                }

                Item { Layout.fillHeight: true } // Spacer

                Button {
                    text: "Exit"
                    Layout.fillWidth: true
                    onClicked: Qt.quit()
                    background: Rectangle {
                        color: parent.hovered ? "#c42b1c" : "transparent"
                        radius: 4
                    }
                    contentItem: Text {
                        text: parent.text
                        color: textColor
                        font.pixelSize: 16
                        verticalAlignment: Text.AlignVCenter
                        leftPadding: 15
                    }
                }
            }
        }

        // Content Area
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: backgroundColor

            StackLayout {
                id: viewStack
                anchors.fill: parent
                anchors.margins: 20
                currentIndex: 0

                HomeView {}
                ArticlesView {}
                BackupsView {}
                ResultsView {}
                SettingsView {}
            }
        }
    }
    
    // Global Error Dialog
    Dialog {
        id: errorDialog
        title: "Error"
        standardButtons: Dialog.Ok
        property alias message: msgText.text
        
        Label {
            id: msgText
            color: "white"
        }
        
        background: Rectangle {
            color: "#2b2b2b"
            border.color: "#555"
        }
    }

    // Papyrus Stats Popup
    Popup {
        id: papyrusPopup
        visible: backend.papyrusMonitoring
        width: 300
        height: 250
        anchors.centerIn: parent
        modal: false
        closePolicy: Popup.NoAutoClose
        
        background: Rectangle {
            color: "#2b2b2b"
            border.color: "#0078d4"
            border.width: 2
            radius: 4
        }
        
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 10
            
            Text {
                text: "Papyrus Monitor"
                color: "white"
                font.bold: true
                font.pixelSize: 18
                Layout.alignment: Qt.AlignHCenter
            }
            
            GridLayout {
                columns: 2
                Layout.alignment: Qt.AlignHCenter
                
                Text { text: "Dumps:"; color: "#ccc" }
                Text { id: statsDumps; text: "0"; color: "white"; font.bold: true }
                
                Text { text: "Stacks:"; color: "#ccc" }
                Text { id: statsStacks; text: "0"; color: "white"; font.bold: true }
                
                Text { text: "Ratio:"; color: "#ccc" }
                Text { id: statsRatio; text: "0.0"; color: "white"; font.bold: true }
                
                Text { text: "Warnings:"; color: "#ccc" }
                Text { id: statsWarns; text: "0"; color: "white"; font.bold: true }
                
                Text { text: "Errors:"; color: "#ccc" }
                Text { id: statsErrors; text: "0"; color: "white"; font.bold: true }
            }
            
            Button {
                text: "Stop Monitoring"
                Layout.alignment: Qt.AlignHCenter
                onClicked: backend.togglePapyrus()
                background: Rectangle {
                    color: parent.hovered ? window.buttonHoverColor : window.buttonColor
                    radius: 4
                }
                contentItem: Text {
                    text: parent.text
                    color: window.textColor
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
            }
        }
    }

    Connections {
        target: backend
        function onPapyrusStatsUpdated(dumps, stacks, ratio, warns, errors) {
            statsDumps.text = dumps
            statsStacks.text = stacks
            statsRatio.text = ratio.toFixed(3)
            statsWarns.text = warns
            statsErrors.text = errors
        }
    }

    Connections {
        target: backend
        function onScanError(title, message) {
            errorDialog.title = title
            errorDialog.message = message
            errorDialog.open()
        }
    }
}
