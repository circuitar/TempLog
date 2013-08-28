"""This is a GUI to plot data collected using the TempLog hardware.

Data is read from the serial port to generate the graph. Just plug in the board and select Tools => Serial port to
start reading.

Copyright (c) 2013 Circuitar
This software is released under an MIT license. See the attached LICENSE file for details.
"""
import re
import os
import serial
import wx
from serial.tools import list_ports
from datetime import datetime
import matplotlib
matplotlib.use('WXAgg')
from matplotlib import pyplot, dates
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import \
    FigureCanvasWxAgg as FigCanvas, \
    NavigationToolbar2WxAgg as NavigationToolbar


class TempLogSerialReader(object):
    """A class to read data from the TempLog hardware through a serial port and store it.

    Attributes:
        time: list of timings for each data point in matplotlib date format (days since 0001-01-01 00:00:00 UTC)
        int_temp: list of internal temperature measurements matching the 'time' attribute
        ext_temp: list of external temperature measurements matching the 'time' attribute
    """

    def __init__(self):
        self._serial = None
        self.reset_data()

    def reset_data(self):
        """Reset all buffers with data collected from the serial port."""
        self.time = []
        self.int_temp = []
        self.ext_temp = []

    def open(self, name, baud_rate=9600):
        """Open or reopen the serial port in non-blocking 8N1 mode.

        Args:
            name: the name of the port to open.
            baud_rate: the baud rate to use.

        Raises:
            ValueError: will be raised when baud_rate parameter is out of range.
            SerialException: raised in case the device cannot be found or cannot be configured.
        """
        self.close()
        self._serial = serial.Serial(name, baud_rate, timeout=0)

    def close(self):
        """Flush and close the serial port if it's open."""
        if self._serial:
            self.reset_data()
            self._serial.flush()
            self._serial.close()

    def read(self):
        """Read serial port data and parse it, storing the result in the internal buffers."""
        if self._serial:
            regex = re.compile(
                '(?P<id>\d+),(?P<year>\d+)-(?P<month>\d+)-(?P<day>\d+),'
                '(?P<hour>\d+):(?P<minute>\d+):(?P<second>\d+),'
                '(?P<int_temp>[\d\.]+),(?P<ext_temp>[\d]+\.\d\d)'
            )
            data = self._serial.readline()
            while data:
                match = regex.match(data)
                if match:
                    groups = match.groupdict()
                    date = datetime(
                        year=int(groups['year']),
                        month=int(groups['month']),
                        day=int(groups['day']),
                        hour=int(groups['hour']),
                        minute=int(groups['minute']),
                        second=int(groups['second'])
                    )
                    self.time += [dates.date2num(date)]
                    self.int_temp += [float(groups['int_temp'])]
                    self.ext_temp += [float(groups['ext_temp'])]
                data = self._serial.readline()


class TempLogPlot(wx.Frame):
    """TempLog graph plotter main window."""

    title = 'TempLog Plot'

    def __init__(self):
        wx.Frame.__init__(self, None, -1, self.title)

        self.serial_reader = TempLogSerialReader()
        self.time = [dates.date2num(datetime.now())]
        self.ext_temp = [25]
        self.paused = False

        self.create_menu()
        self.create_status_bar()
        self.create_main_panel()

        self.redraw_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)
        self.redraw_timer.Start(100)

    def create_menu(self):
        self.menubar = wx.MenuBar()

        menu_file = wx.Menu()
        m_expt = menu_file.Append(-1, "&Save plot\tCtrl-S", "Save plot to file")
        self.Bind(wx.EVT_MENU, self.on_save_plot, m_expt)
        menu_file.AppendSeparator()
        m_exit = menu_file.Append(-1, "E&xit\tCtrl-X", "Exit")
        self.Bind(wx.EVT_MENU, self.on_exit, m_exit)

        menu_tools = wx.Menu()
        m_expt = menu_tools.Append(-1, "Serial &port\tCtrl-P", "Select and open serial port")
        self.Bind(wx.EVT_MENU, self.on_serial_port, m_expt)

        self.menubar.Append(menu_file, "&File")
        self.menubar.Append(menu_tools, "&Tools")
        self.SetMenuBar(self.menubar)

    def create_main_panel(self):
        self.panel = wx.Panel(self)

        self.init_plot()
        self.canvas = FigCanvas(self.panel, -1, self.fig)

        self.toolbar = NavigationToolbar(self.canvas)

        self.pause_button = wx.Button(self.panel, -1, 'Pause')
        self.Bind(wx.EVT_BUTTON, self.on_pause_button, self.pause_button)
        self.Bind(wx.EVT_UPDATE_UI, self.on_update_pause_button, self.pause_button)

        self.cb_grid = wx.CheckBox(self.panel, -1, 'Show Grid', style=wx.ALIGN_RIGHT)
        self.Bind(wx.EVT_CHECKBOX, self.on_cb_grid, self.cb_grid)
        self.cb_grid.SetValue(True)

        self.hbox0 = wx.BoxSizer(wx.HORIZONTAL)
        self.hbox0.Add(self.pause_button, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        self.hbox0.AddSpacer(20)
        self.hbox0.Add(self.cb_grid, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)

        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.canvas, 1, flag=wx.LEFT | wx.TOP | wx.GROW)
        self.vbox.Add(self.toolbar, 0, wx.EXPAND)
        self.vbox.Add(self.hbox0, 0, flag=wx.ALIGN_LEFT | wx.TOP)

        self.panel.SetSizer(self.vbox)
        self.vbox.Fit(self)

    def create_status_bar(self):
        self.status_bar = self.CreateStatusBar()
        self.status_bar.SetFieldsCount(2)
        self.status_bar.SetStatusWidths([-1, 200])
        self.status_bar.SetStatusText('Not connected', 1)

    def init_plot(self):
        self.dpi = 100
        self.fig = Figure((8.0, 6.0), dpi=self.dpi)

        self.axes = self.fig.add_subplot(111)
        self.axes.set_axis_bgcolor('black')
        self.axes.set_title('Temperature', size=12)

        pyplot.setp(self.axes.get_xticklabels(), fontsize=8)
        pyplot.setp(self.axes.get_yticklabels(), fontsize=8)

        self.plot_data = self.axes.plot(
            self.time,
            self.ext_temp,
            linewidth=1,
            color=(1, 1, 0),
        )[0]

    def draw_plot(self):
        """ Redraws the plot."""

        # Use a major scale of one minute
        xmax = max(self.time)
        xmin = xmax - 0.004
        ymin = round(min(self.ext_temp), 0) - 1
        ymax = round(max(self.ext_temp), 0) + 1

        self.axes.set_xbound(lower=xmin, upper=xmax)
        self.axes.set_ybound(lower=ymin, upper=ymax)

        locator = dates.MinuteLocator()
        formatter = dates.DateFormatter('%H:%M')
        self.axes.xaxis.set_major_locator(locator)
        self.axes.xaxis.set_major_formatter(formatter)

        if self.cb_grid.IsChecked():
            self.axes.grid(True, color='gray')
        else:
            self.axes.grid(False)

        self.plot_data.set_xdata(self.time)
        self.plot_data.set_ydata(self.ext_temp)

        self.canvas.draw()

    def on_pause_button(self, event):
        self.paused = not self.paused

    def on_update_pause_button(self, event):
        label = "Resume" if self.paused else "Pause"
        self.pause_button.SetLabel(label)

    def on_serial_port(self, event):
        sp = wx.GetSingleChoice('Select a serial port', 'Serial port', [x for x, y, z in list_ports.comports()])
        if sp:
            self.serial_reader.open(sp, 115200)
            self.status_bar.SetStatusText(sp, 1)

    def on_cb_grid(self, event):
        self.draw_plot()

    def on_save_plot(self, event):
        file_choices = "PNG (*.png)|*.png"

        dlg = wx.FileDialog(
            self,
            message="Save plot as...",
            defaultDir=os.getcwd(),
            defaultFile="plot.png",
            wildcard=file_choices,
            style=wx.SAVE)

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.canvas.print_figure(path, dpi=self.dpi)
            self.flash_status_message("Saved to %s" % path)

    def on_redraw_timer(self, event):
        self.serial_reader.read()
        if not self.paused:
            if self.serial_reader.time:
                self.time = list(self.serial_reader.time)
                self.ext_temp = list(self.serial_reader.ext_temp)
            self.draw_plot()

    def on_exit(self, event):
        self.serial_reader.close()
        self.Destroy()

    def flash_status_message(self, msg, flash_len_ms=1500):
        self.status_bar.SetStatusText(msg)
        self.timeroff = wx.Timer(self)
        self.Bind(
            wx.EVT_TIMER,
            self.on_flash_status_off,
            self.timeroff)
        self.timeroff.Start(flash_len_ms, oneShot=True)

    def on_flash_status_off(self, event):
        self.status_bar.SetStatusText('', 0)


if __name__ == '__main__':
    app = wx.App()
    app.frame = TempLogPlot()
    app.frame.Show()
    app.MainLoop()
