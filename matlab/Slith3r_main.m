close all;
clear all;
clc;

%% Preferenches
% boolExample = 1 ;  %1 to load example, 0 to load your own parameters
% if boolExample == 1
%     [ANGLES,dim,prtOpt,pltOpt] = chooseExample(boolExample);
% else
%     %Load your own parameters here, generated in parametersInput
%     loadfolder = './STARRYNIGHT_outputs/'; 
%     load(strcat(loadfolder,'ANGLES.mat')); % ANGLES FORMAT EXPECTED: Struct with fields 'U' 'V', 'X', 'Y'
%     load(strcat(loadfolder,'DIM.mat')); %[dimx dimy]; 
%     load(strcat(loadfolder,'prtOpt.mat')); % Structure defining toolpath and printing-related parameters in parametersInput.m
%     load(strcat(loadfolder,'pltOpt.mat')); % Structure defining plotting-related parameters in parametersInput.m
% end
% 
% if ~exist(pltOpt.foldername, 'dir')
%    mkdir(pltOpt.foldername)
% end
    loadfolder = './examples/'; 
load(strcat(loadfolder,'MM_topt_Mu_alex_mirror_2.mat')); % ANGLES FORMAT EXPECTED: Struct with fields 'U' 'V', 'X', 'Y'

%ANGLES = 
load(strcat(loadfolder,'ANGLES.mat')); % ANGLES FORMAT EXPECTED: Struct with fields 'U' 'V', 'X', 'Y'
%dim = 
load(strcat(loadfolder,'dim.mat')); % ANGLES FORMAT EXPECTED: Struct with fields 'U' 'V', 'X', 'Y'
ANGLES.U(:,1:25) = -ANGLES.U(:,1:25);
ANGLES.V(:,1:25) = -ANGLES.V(:,1:25);

%%
%make orthogonal flow field
orth.U = -ANGLES.V;
orth.V = ANGLES.U;

ANGLES.U = orth.U;
ANGLES.V = orth.V;


%%


prtOpt.gcode_fname = 'MMtopopt_output/new_WOODBW_700_X160_Y90.gcode';
%faster
% pltOpt.save_matlabfiles = 'yes';
% prtOpt.layer_height = 0.2;
% prtOpt.upperbound = 2;
% prtOpt.lowerbound = 0.8;
% prtOpt.widthInterp = 0.22;
% prtOpt.distInterp = 5;
% prtOpt.thresh_traveldist = 2;
%alex:
    prtOpt.I = imread('./examples/Images/bamboo.png'); %change here the path to a B&W image (printed path in white)
    % prtOpt.I2 = imread('./examples/Images/double_bamboo.png'); %change here the path to a B&W image (printed path in white)
imshow(prtOpt.I);

pltOpt.save_matlabfiles = 'yes';
prtOpt.layer_height = 0.2;
prtOpt.upperbound = 0.6;
prtOpt.lowerbound = 0.4;
prtOpt.widthInterp = 0.22;
prtOpt.distInterp = 5;
prtOpt.targetwidth = 0.5;
prtOpt.threshDist = 1.2;
prtOpt.thresh_traveldist = 2;
prtOpt.nLayers = 1;
prtOpt.temp_carbon = 235;
prtOpt.temp_bamboo = 230;
prtOpt.x_printstart = 250;
prtOpt.y_printstart = 100;
prtOpt.print_speed = 2400;
%% create streamlines
if strcmpi(pltOpt.plot_quiver, 'yes')
    PlotQuiver(pltOpt,ANGLES)
end 

Nmem = 100;    
integStep = 0.15; 

if strcmp(prtOpt.ControlSeedPoint,'yes')
    LAYER = regularStreamlines(ANGLES, prtOpt, integStep, Nmem,pltOpt); 
else
    LAYER = evenStreamlines(ANGLES, prtOpt,integStep, Nmem,pltOpt); 
end


if strcmpi(pltOpt.save_matlabfiles, 'yes')
     save(pltOpt.filename_LAYERstruct, 'LAYER')
end 

%% Streamlines to Print paths 

imshow(prtOpt.I);


% Trim points outside shape 
if prtOpt.frameBool == 1 
    a_SL = gca; 
    layer = CutShape(LAYER, ANGLES, dim, prtOpt) ;
else layer = LAYER;
end
%% new *******************************####Mu#####
% Load mesh info
base = 'C:\Users\afluijten\OneDrive - Delft University of Technology\Documents\MATLAB\slith3r-main\examples\multimaterial_matlab_output\';
mesh = load(fullfile(base, 'mesh_data_loops.mat'), 'centroids', 'bamboo_ids', 'carbon_ids');

% Combine bamboo and carbon IDs
valid_ids = union(mesh.bamboo_ids, mesh.carbon_ids);
valid_pts = mesh.centroids(valid_ids, :);  % Nx2
%%
% Visualize bamboo and carbon points before creating the mask
figure; hold on; axis equal;
plot(mesh.centroids(mesh.bamboo_ids,1), mesh.centroids(mesh.bamboo_ids,2), 'g.', 'DisplayName', 'Bamboo');
plot(mesh.centroids(mesh.carbon_ids,1), mesh.centroids(mesh.carbon_ids,2), 'k.', 'DisplayName', 'Carbon');
legend;
title('Centroid Material Labels: Green = Bamboo, Black = Carbon');
xlabel('X'); ylabel('Y');
%
% Image resolution
img_res = 4000;

% Extract ANGLES grid limits
allX = [ANGLES.X]; allY = [ANGLES.Y];
minX = min(allX(:)); maxX = max(allX(:));
minY = min(allY(:)); maxY = max(allY(:));

% Normalize material centroids to image pixel coordinates
x = valid_pts(:,1);
y = valid_pts(:,2);
x_img = round((x - minX) / (maxX - minX) * (img_res - 1)) + 1;
y_img = img_res - round((y - minY) / (maxY - minY) * (img_res - 1));  % flip Y

% Clip indices to valid range
x_img = min(max(x_img, 1), img_res);
y_img = min(max(y_img, 1), img_res);

% Create binary mask
bw = false(img_res, img_res);
for i = 1:length(x_img)
    bw(y_img(i), x_img(i)) = true;
end

% Optional: dilate for continuity
bw = imdilate(bw, strel('disk', 50));
% Convert to RGB image expected by CutShapeNew
prtOpt.I = repmat(uint8(bw) * 255, [1, 1, 3]);

    prtOpt.I = imread('./examples/Images/bamboo.png'); %change here the path to a B&W image (printed path in white)

% Visual check
figure;
imshow(prtOpt.I);
axis on;
title('Material Mask (used in CutShapeNew)');
% Update dim based on ANGLES (physical dimensions)
dim = [maxX - minX, maxY - minY];

% Apply mask-based cutting
layer = CutShapeNew(LAYER, ANGLES, dim, prtOpt);

% new *******************************####Mu#####
% new ******************************* ###end#####
%% Reduce amount of points within one path (avoid overload of printer
% buffer), remove paths if too short and offset by x_printstart and
% y_printstart
layerSimplify = SimplifyPaths(layer, prtOpt,pltOpt); 

plotGcode(layerSimplify)


% Reorder courses for printing (minimize travel length between closest extremities)
layerMoved = movePrint(layerSimplify,[prtOpt.x_printstart prtOpt.y_printstart],1);

layerReorder = ReorderPaths(layerMoved,prtOpt);


if strcmpi(pltOpt.save_matlabfiles, 'yes')
    save(strcat(pltOpt.filename_LAYERstruct, '_reordered'), 'layerReorder');
end

% Statistics- visualize distribution of line widths 
DistanceHistogram(layerReorder,pltOpt,prtOpt);

%%
%new #############################################################new *******************************####Mu#####
base = 'C:\Users\afluijten\OneDrive - Delft University of Technology\Documents\MATLAB\slith3r-main\examples\multimaterial_matlab_output\';
% 1) Load mesh centroids
data = load(fullfile(base,'mesh_data_loops.mat'),'centroids','bamboo_ids','carbon_ids');
mesh.centroids  = data.centroids;
mesh.bamboo_ids = data.bamboo_ids;
mesh.carbon_ids = data.carbon_ids;
% 2) Store them explicitly in prtOpt
prtOpt.bambooPts = mesh.centroids(mesh.bamboo_ids, :);
prtOpt.carbonPts = mesh.centroids(mesh.carbon_ids, :);
prtOpt.materialRadius = 0.8;   % how far to search    

%% 4) Save everything
saveSegPrepData(ANGLES, layerReorder, prtOpt, pltOpt, img_res);
debugSegmentation();
%new ####end############################################################new *******************************####Mu#####

%%
% Create gcode
% if strcmpi(pltOpt.save_matlabfiles, 'yes')
%      GCodeFormat(layerReorder,prtOpt);
% end
