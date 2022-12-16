# This class is used to create the plot inside the graph window and allow the user to click the canvas and record the
# coordinates of a mouse click. It was required to adjust axis sizes to allow the x and y axis labels to be displayed
# correctly in a window.

# The code is modified from:
# https://stackoverflow.com/questions/43947318/plotting-matplotlib-figure-inside-qwidget-using-qt-designer-form-and-pyqt5

# Imports
from PyQt5 import QtWidgets
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas
import matplotlib
import matplotlib.pyplot as plt

# Ensure using PyQt5 backend
matplotlib.use('QT5Agg')

# Matplotlib canvas class to create figure
class MplCanvas(Canvas):
    def __init__(self):
        self.fig = Figure()
        # [left, bottom, width, height]
        self.ax = self.fig.add_axes([0.15, 0.19, 0.8, 0.75])
        plt.tight_layout()
        Canvas.__init__(self, self.fig)
        Canvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        Canvas.updateGeometry(self)

    def full_plot(self):
        self.ax.set_position([0, 0, 1, 1])

    def save_fig(self, file):
        self.fig.savefig(file)


# Matplotlib widget
class MplWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)   # Inherit from QWidget
        self.canvas = MplCanvas()                  # Create canvas object
        self.vbl = QtWidgets.QVBoxLayout()         # Set box for plotting
        self.vbl.addWidget(self.canvas)
        self.setLayout(self.vbl)

    def setText(self, *args, **kwargs):
        pass
