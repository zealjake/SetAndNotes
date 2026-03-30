from __future__ import annotations


def application_stylesheet() -> str:
    return """
    QMainWindow {
        background: #141617;
        color: #f1ede6;
    }

    QToolBar#projectToolbar,
    QToolBar#workflowToolbar {
        background: #1b1e1f;
        border: 1px solid #313638;
        spacing: 8px;
        padding: 8px;
    }

    QToolBar#projectToolbar {
        background: #181b1c;
    }

    QToolBar#workflowToolbar {
        background: #1d2021;
    }

    QToolButton {
        background: #232728;
        border: 1px solid #3a4042;
        border-radius: 5px;
        padding: 6px 10px;
        color: #f1ede6;
    }

    QToolButton:hover {
        background: #2b2f31;
    }

    QTableView {
        background: #191c1d;
        alternate-background-color: #212628;
        gridline-color: #34393b;
        border: 1px solid #313638;
        selection-background-color: #40525d;
        selection-color: #f6f0e8;
    }

    QHeaderView::section {
        background: #202426;
        color: #f1ede6;
        border: 1px solid #313638;
        padding: 6px;
    }

    QTableView::item {
        padding: 7px 10px;
        border-bottom: 1px solid #2a2f31;
    }

    QTableView::item:hover {
        background: #2a3134;
    }

    QTableView::item:selected {
        background: #4b6776;
        color: #fff8ef;
    }

    QTableView::item:selected:active,
    QTableView::item:selected:!active {
        background: #4b6776;
        color: #fff8ef;
    }

    QWidget#detailPanel,
    QStatusBar#statusPanel {
        background: #1b1e1f;
        border: 1px solid #313638;
        border-radius: 5px;
    }
    """
