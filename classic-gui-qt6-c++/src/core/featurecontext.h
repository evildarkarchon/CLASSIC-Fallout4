#pragma once

class MainWindow;
class SignalHub;
class ThreadManager;

struct FeatureContext {
    MainWindow* mainWindow = nullptr;
    SignalHub* signalHub = nullptr;
    ThreadManager* threadManager = nullptr;
};
