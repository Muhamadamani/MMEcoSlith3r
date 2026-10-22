close all
clear all
clc

loadfolder = './examples/'; 
load(strcat(loadfolder,'MM_topt_Mu_alex_mirror_2.mat')); % ANGLES FORMAT EXPECTED: Struct with fields 'U' 'V', 'X', 'Y'

load(strcat(loadfolder,'ANGLES.mat')); % ANGLES FORMAT EXPECTED: Struct with fields 'U' 'V', 'X', 'Y'
%dim = 
load(strcat(loadfolder,'dim.mat')); % ANGLES FORMAT EXPECTED: Struct with fields 'U' 'V', 'X', 'Y'
ANGLES.U(:,1:25) = -ANGLES.U(:,1:25);
ANGLES.V(:,1:25) = -ANGLES.V(:,1:25);

    %PlotQuiver(pltOpt,ANGLES)



    % Load or assume ANGLES.U and ANGLES.V are already in the workspace
% These should be 2D matrices representing the flow field components

% Compute orthogonal components (90° counterclockwise rotation)
orth.U = -ANGLES.V;
orth.V = ANGLES.U;
orth.X = ANGLES.X;
orth.Y = ANGLES.Y;

% % Optionally create a grid for plotting (assuming size of U and V)
% [nRows, nCols] = size(ANGLES.U);
% [X, Y] = meshgrid(1:nCols, 1:nRows);

% Plot original and orthogonal flow fields
figure;

%subplot(1, 2, 1);
    PlotQuiver(pltOpt,ANGLES)

%quiver(X, Y, ANGLES.U, ANGLES.V, 'b');
title('Original Flow Field');
axis equal tight;
xlabel('X'); ylabel('Y');
figure
%subplot(1, 2, 2);
%quiver(X, Y, U_orth, V_orth, 'r');
    PlotQuiver(pltOpt,orth)

title('Orthogonal Flow Field');
axis equal tight;
xlabel('X'); ylabel('Y');
