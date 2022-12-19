<div id="top"></div>
<!--
*** Readme based on the template here: https://github.com/othneildrew/Best-README-Template
-->

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/DaleLOB/FLUTE">
    <img src="icons/logo_name.png" alt="Logo" width="352" height="88">
  </a>

  <p align="center">
    An exploration tool for FLIM data
    <br />
    <a href="https://github.com/DaleLOB/FLUTE"><strong>Explore the docs »</strong></a>
    <br />

  </p>
</div>


<!-- ABOUT THE PROJECT -->
## About the project
<div align="center">
<img src="icons/MainWindow.PNG" width="500"> 
</div>

Fluorescence Lifetime Ultimate Explorer (FLUTE) provides a graphical user interface to explore fluorescence lifetime data using phasor analysis. The tool allows for quick and interactive analysis of experimental data, and can export results for further processing. 

An example of various analyses can be seen here:

<div align="center">
<img src="icons/Demonstration.PNG" align="center">

*Intensity colourmap with region selection, phase colourmap, modulus colourmap, and fraction colourmap of the same data. Scale bar is 150 um.*
</div>

<p align="right">(<a href="#top">back to top</a>)</p>



### Built with

FLUTE mainly depends on the following packages:

* [PyQt](https://pypi.org/project/PyQt5/)
* [Scipy](https://scipy.org)
* [Numpy](https://numpy.org)

With the exe compiled using
```auto-py-to-exe```


<!-- GETTING STARTED -->
## Getting started

### Running the exe
To quickly start using FLUTE, an exe which works on Windows computers without installing Python is available under releases on the github.

### Running the code
To run the code from this github page, run main.py after installing:

```pip install PyQt5, numpy, opencv-python, matplotlib, scikit-image```

### Prerequisites

Data must be saved as a tiff-stack, where each page of the stack represents a bin in the measurement of the fluorescence decay. Example data is avilable in the supplemental data of the release publication.

<p align="right">(<a href="#top">back to top</a>)</p>

## User manual and publication

A detailed user manual is available in the supplemental material of the associated publication:

Please cite this article if you found FLUTE helpful with your data analysis.



