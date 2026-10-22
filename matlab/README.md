# Slith3r
Slith3r: a slicer with slitherin' toolpaths. 

Slith3r is a easy-to-use tool to embed and study free-form patterns in Mechanics. 

It generates g-code for your 3D printer based on an angle-field.

## How to use


### Dependencies
Slith3r requires  MATLAB `R2021b` and the following add-ons:
- Mapping Toolbox
- Statistics and Machine Learning Toolbox
- Colorbrewer: Attractive and Distinctive Colormaps
### Examples from the article

To try out an example from the article: 
-	Open Slith3r_main.m 
-	Set `boolExample == 1` 
-	Run Slith3r
-	Select the example you wish to try from the dropdown menu.

### Own angle field

If you wish to try Slith3r with your own angle distribution, you need four main variables:
-	`ANGLES` - a struct containing following fields, X, Y, U, V. These are matrices of same dimensions representing point and angle coordinates where `[X,Y] = meshgrid(x,y)`. See `angleFieldINPUT.m`. 
-	`dim` -  [dimx dimy];
-	`prtOpt` - a struct containing various options related to toolpath and printing generation
-	`pltOpt`- idem for plots 

Generating `ANGLES` and `dim` is made easy by running `angleFieldINPUT.m`. There you can also re-generate the angle fields of the examples proposed in Slith3r and shown in the article to get started. 

Generating `prtOpt` and `pltOpt` is made easy by running `parametersInput.m`, which creates the variables `pltOpt` and `prtOpt` in the specified folder. 

Once this is done, you can :
1. Save these four variables in a folder
2. Open `Slith3r.main`  and set `boolExample == 1` 
3. Change folder name in `loadfolder`
4. Run the script

### Generate G-code 
By default, example files do not save G-codes, but this is possible by changing `pltOpt.save_matlabfiles`. 

Remember to also change `prtOpt` and the G-code being and end in the `begin_endGcodes` folder to adapt to your printer and material. 

## Develop
For small matters, please create an issue on https://gitlab.tudelft.nl/shapingmatterlab/slith3r.

For now, Slith3r is a research project and is not made to function as a conventional slicer which typically divides an STL file in multiple layers. If you are interested in helping us add the freedom of toolpath from Slith3r into Slic3r, please contact us!

## Cite this project
Please cite this repository along with our research paper!

## License

[GPL v3](https://www.gnu.org/licenses/gpl-3.0.html), click for
[more info](https://gist.github.com/kn9ts/cbe95340d29fc1aaeaa5dd5c059d2e60) on this licence


## Acknowledgments 
`dpsimplify.m` - Wolfgang Schwanghart (2023). Line Simplification (https://www.mathworks.com/matlabcentral/fileexchange/21132-line-simplification), MATLAB Central File Exchange. Retrieved Jan 28, 2022. 

`mmstream2.m` - Duane Hanselman (2023). Improved 2-D Streamlines (https://www.mathworks.com/matlabcentral/fileexchange/38860-improved-2-d-streamlines), MATLAB Central File Exchange. Retrieved July 25, 2022.