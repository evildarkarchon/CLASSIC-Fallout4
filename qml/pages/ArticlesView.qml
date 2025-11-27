import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20

        Text {
            text: "Useful Resources & Links"
            font.pixelSize: 24
            font.bold: true
            color: "white"
            Layout.alignment: Qt.AlignHCenter
        }

        GridView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            cellWidth: width / 3
            cellHeight: 80
            clip: true

            model: ListModel {
                ListElement { name: "BUFFOUT 4 INSTALLATION"; url: "https://www.nexusmods.com/fallout4/articles/3115" }
                ListElement { name: "FALLOUT 4 SETUP TIPS"; url: "https://www.nexusmods.com/fallout4/articles/4141" }
                ListElement { name: "IMPORTANT PATCHES LIST"; url: "https://www.nexusmods.com/fallout4/articles/3769" }
                ListElement { name: "BUFFOUT 4 NEXUS"; url: "https://www.nexusmods.com/fallout4/mods/47359" }
                ListElement { name: "CLASSIC NEXUS"; url: "https://www.nexusmods.com/fallout4/mods/56255" }
                ListElement { name: "CLASSIC GITHUB"; url: "https://github.com/evildarkarchon/CLASSIC-Fallout4" }
                ListElement { name: "DDS TEXTURE SCANNER"; url: "https://www.nexusmods.com/fallout4/mods/71588" }
                ListElement { name: "BETHINI PIE"; url: "https://www.nexusmods.com/site/mods/631" }
                ListElement { name: "WRYE BASH"; url: "https://www.nexusmods.com/fallout4/mods/20032" }
            }

            delegate: Button {
                width: GridView.view.cellWidth - 10
                height: GridView.view.cellHeight - 10
                
                background: Rectangle {
                    color: parent.hovered ? "#444" : "#333"
                    radius: 6
                    border.color: "#555"
                }

                contentItem: Text {
                    text: model.name
                    color: "white"
                    font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    wrapMode: Text.WordWrap
                }

                onClicked: Qt.openUrlExternally(model.url)
            }
        }
    }
}
