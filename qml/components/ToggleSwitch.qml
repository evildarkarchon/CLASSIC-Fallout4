import QtQuick 2.15
import QtQuick.Controls 2.15

Switch {
    id: control
    
    property color accentColor: "#0078d4"
    property color uncheckedColor: "#333333"
    property color handleColor: "#ffffff"
    property color textColor: "#ffffff"

    indicator: Rectangle {
        implicitWidth: 40
        implicitHeight: 20
        x: control.leftPadding
        y: parent.height / 2 - height / 2
        radius: 10
        color: control.checked ? control.accentColor : control.uncheckedColor
        border.color: control.checked ? control.accentColor : "#555555"
        
        Rectangle {
            x: control.checked ? parent.width - width - 2 : 2
            y: 2
            width: 16
            height: 16
            radius: 8
            color: control.handleColor
            Behavior on x {
                NumberAnimation { duration: 150 }
            }
        }
    }

    contentItem: Text {
        text: control.text
        font: control.font
        opacity: enabled ? 1.0 : 0.3
        color: control.textColor
        verticalAlignment: Text.AlignVCenter
        leftPadding: control.indicator.width + control.spacing
    }
}
