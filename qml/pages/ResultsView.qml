import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 10

        RowLayout {
            Button {
                text: "Refresh"
                onClicked: backend.refreshReports()
                background: Rectangle {
                    color: parent.hovered ? window.buttonHoverColor : window.buttonColor
                    radius: 4
                    border.color: "#555"
                }
                contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
            Button {
                text: "Delete Selected"
                onClicked: {
                    if (reportList.currentIndex >= 0) {
                        backend.deleteReport(reportList.model[reportList.currentIndex].path)
                    }
                }
                background: Rectangle {
                    color: parent.hovered ? window.buttonHoverColor : window.buttonColor
                    radius: 4
                    border.color: "#555"
                }
                contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
            }
            Item { Layout.fillWidth: true }
        }

        SplitView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            orientation: Qt.Horizontal
            
            handle: Rectangle {
                implicitWidth: 4
                color: SplitHandle.pressed ? "#0078d4" : (SplitHandle.hovered ? "#666" : "#444")
            }

            // Report List
            Rectangle {
                SplitView.preferredWidth: 250
                SplitView.minimumWidth: 150
                color: "#252526"
                border.color: "#333"

                ListView {
                    id: reportList
                    anchors.fill: parent
                    anchors.margins: 5
                    clip: true
                    focus: true
                    
                    model: backend.getReports() // Initial load might be empty, need signals
                    
                    delegate: ItemDelegate {
                        width: ListView.view.width
                        text: modelData.name
                        
                        contentItem: Text {
                            text: modelData.name
                            color: "white"
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter
                        }
                        
                        background: Rectangle {
                            color: parent.highlighted || parent.hovered ? "#37373d" : "transparent"
                        }
                        
                        highlighted: ListView.isCurrentItem
                        onClicked: {
                            reportList.currentIndex = index
                            reportView.text = backend.readReport(modelData.path)
                        }
                    }
                    
                    // Auto-select first
                    onModelChanged: {
                        if (count > 0) {
                            currentIndex = 0
                            reportView.text = backend.readReport(model[0].path)
                        }
                    }
                }
                
                Connections {
                    target: backend
                    function onReportsUpdated() {
                        reportList.model = backend.getReports()
                    }
                }
            }

            // Report Viewer
            Rectangle {
                SplitView.fillWidth: true
                color: "#1e1e1e"
                border.color: "#333"

                ScrollView {
                    anchors.fill: parent
                    TextArea {
                        id: reportView
                        readOnly: true
                        textFormat: TextEdit.MarkdownText
                        wrapMode: Text.WordWrap
                        color: "#d4d4d4"
                        background: null
                        font.family: "Consolas"
                        font.pixelSize: 14
                        padding: 10
                        selectByMouse: true
                    }
                }
            }
        }
    }
}
