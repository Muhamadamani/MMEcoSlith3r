

%________________________%
%--- PRINTING CHOICES ---%
%________________________%
prtOpt.nLayers = 1; %this is only for replication of one layer. If size(ANGLES)>1, this will be overrun. 
prtOpt.nRepeats = 1; % this will create a gcode with nRepeats instances of the part. For now they are positioned from left to right

prtOpt.upperbound = 5; %mm; sets maximum spacing between streamlines: UPPER BOUND OF LINE WIDTH 
prtOpt.lowerbound = prtOpt.upperbound/3.5; % this determines LOWER BOUND of line width; default value upperbound/3.5; 

prtOpt.ControlSeedPoint = 'no'; %yes to call a routine that first seeds streamlines along one specified edge evenly with a distance of targetwidth
prtOpt.targetwidth = prtOpt.upperbound/1.2; %mm %only activated when ControlSeedPoint = 'yes' ; should be lowerbound<targetwidth<upperbound

prtOpt.boolFilter = 1; % 1 will Cull paths that are shorter than threshDist, 0 will not cull any path even if they're very short 
prtOpt.threshDist = 0.9; 

prtOpt.tol = 0.05; %tolerance in mm for the Douglas-Peucker point reduction algorithm 
prtOpt.widthInterp = 0.25; % %threshold width jump between 2 points to trigger interpolation; default value: prtOpt.widthInterp = 0.25;
prtOpt.distInterp = 5; %distance between 2 points to trigger interpolation; default value: prtOpt.distInterp = 5;

prtOpt.ironingFrame = 'no'; %yes if extra toolpaths should be added to smear the long edges
prtOpt.Spirals = 'no'; %yes if it's likely that the angle field will result in spirals. This calls for extra checks but costs more time.


%--- SPEEDS ---%
prtOpt.print_speed = 20;       % mm/s
prtOpt.travel_speed = 75;      %mm/s

%--- PRINTER SETTINGS ---%
prtOpt.fil_dia = 1.75;         % mm

%--- Z-VALUES ---%
prtOpt.layer_height = 0.1; %mm 
prtOpt.thresh_traveldist = 10; %[mm] %distance between courses from which retraction should be considered

% set up practical printer/code units
prtOpt.print_speed = prtOpt.print_speed*60;       % mm/min
prtOpt.travel_speed = prtOpt.travel_speed*60;      %mm/min

%--- POSITIONS ---%
prtOpt.x_printstart = 160; %[mm] %value to add to all X values for translation ; if on the part 0 is the center, add half width + half height! 
prtOpt.y_printstart = 90; %[mm] %value to add to all Y values for translation 

%____________________________________%
%--- PLOTTING/SAVING PREFERENCES ---%
%____________________________________%

pltOpt.plot_quiver = 'yes'; %quiver plot 
pltOpt.plot_createStreamlines = 'yes'; 
pltOpt.plot_Distance = 'yes';
pltOpt.plot_scatterwithDistance = 'yes' ;
pltOpt.plot_curvesimplification = 'no' ;
pltOpt.plot_histDistance = 'yes';
pltOpt.plot_Triangles = 'no';
pltOpt.plot_mask = 'yes';

%--- SAVING PREFERENCES ---%
pltOpt.save_plots = 'no' ;
pltOpt.save_matlabfiles = 'no' ; 

%--- FILE NAMES ---%
fname =  'Chair'; 
pltOpt.foldername = strcat(fname,'_outputs/');
prtOpt.gcode_fname = strcat(pltOpt.foldername, fname,'BW_', string(prtOpt.upperbound*1000).replace('.','p'),sprintf('_X%d_Y%d',prtOpt.x_printstart,prtOpt.y_printstart) ,'.gcode');
prtOpt.gcodeExtremes_foldername = './begin_endGcodes/'; %where beginning & end gcode files can be found, to be changed with printer
pltOpt.filename_LAYERstruct = strcat(pltOpt.foldername,fname,'_BW_', string(prtOpt.upperbound*1000).replace('.','p'), 'mm'); %after streamline generation, before post processing

if strcmp(prtOpt.ControlSeedPoint,'yes')
%     prtOpt.targetwidth = 0.4; %mm %only activated when ControlSeedPoint = 'yes' 
%     prtOpt.Edge = [min(ANGLES.X,[], 'ALL') min(ANGLES.Y,[], 'ALL');
%                      max(ANGLES.X,[], 'ALL') min(ANGLES.Y,[], 'ALL')]; %[x1 y1; x2 y2] ; ideally this edge is perpendicular to most
    prtOpt.Edge = [min(ANGLES.X,[], 'ALL') max(ANGLES.Y,[], 'ALL');
                     max(ANGLES.X,[], 'ALL') max(ANGLES.Y,[], 'ALL')]; %[x1 y1; x2 y2] ; ideally this edge is perpendicular to most
    % future streamlines 
end



%_____________%
%--- SHAPE ---%
%_____________%

prtOpt.frameBool = 1; % If you desire the part to be cut according to a shape, defined by a B&W image

%  --- what is a good image? --- %
% B&W, no transparency, White = what is printed, and there should be at 
% least 1 pixel of black all around

if prtOpt.frameBool == 1
    prtOpt.I = imread('./examples/Images/Chair.png'); %change here the path to a B&W image (printed path in white)
end



%_____________%
%--- SAVE ---%
%_____________%

if ~exist(pltOpt.foldername, 'dir')
   mkdir(pltOpt.foldername)
end
save(strcat(pltOpt.foldername, 'prtOpt'), 'prtOpt');
save(strcat(pltOpt.foldername, 'pltOpt'),'pltOpt'); 
