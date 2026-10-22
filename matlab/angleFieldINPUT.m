% This script shows how to obtain the angle fields described in the
% article. Streamlines are displayed as a useful way of observing the angle fields,
% however these are not evenly distributed according to our method.

clearvars
close all

% SELECT EXAMPLE  
list = {'Wood','Cardioid','Vortex','Radial',...                   
'Hyperbol','Chair','Payload Adaptor', 'The Starry Night', 'Figure 1', 'I want to try my own!'};
[indx,tf] = listdlg('PromptString',{'Select an angle field to try.'},...
    'SelectionMode','single','ListString',list,'ListSize',[150,150]);

example = list{indx}; 

% Initialization of default relevant dimensions 
dimx = 30;
dimy = 30;% 25; 
scale = 1;  %tune for the number of nodes per mm
Nx = floor(dimx/scale); %number of nodes in x
Ny = floor(dimy/scale); %40; %15;
x = linspace(-dimx/2,dimx/2,Nx);
y = linspace(-dimy/2,dimy/2,Ny);

[X,Y] = meshgrid(x,y);
[Theta, R] = cart2pol(X,Y);
Z = X + 1i.*Y ; 

% Do you want to save the files? 
fname =  example; 
foldername = strcat(fname,'_outputs/');
save_matlabfiles = 'yes'; 

switch example 
    case 'Cardioid'
        W = (X-1i*(Y+15)).^(-2); 
    case 'Vortex'
        S = 1; %postive real
        V = -3; 
        W = (S + 1i*V)./(2*pi.*(Z)); 
    case 'Radial'
        V = 0; %postive real
        D = 1; 
        W = (D - 1i*V)./(2*pi.*(Z)); 
    case 'Hyperbol'
        W = X + 1i*Y; 
    case 'Chair'
        imgName = './examples/Images/Chair.png';
        [dimx, dimy, X,Y,W] = chairExample();
        figure;
        plotFrame(imgName,dimx,dimy)
        hold on
    case 'Payload Adaptor' %two layers are created 
        imgName = './examples/Images/PayloadAdaptor.png';
        [dimx, dimy,X,Y,ANGLES] = payloadadaptorExample();
        resizeImg = 12; 
    case 'The Starry Night'
        imgName = './examples/Images/StarryNight.jpg';
        [dimx, dimy,X,Y,W] = starrynightExample();
    case 'Figure 1'
        a = 1; 
        lambda = dimy/3;
        W = a*(cos(X./lambda) + 1i*cos(Y./lambda)); 
    case 'Wood'
        imgName = './examples/Images/Wood_MarkWindom.jpg';
        [dimx, dimy,X,Y,W] = woodExample();
    case 'I want to try my own!'
        %%% FILL YOUR EQUATION HERE %%%
        %  [dimx, dimy,X,Y,W] = ...
        msg = "Please fill in your own equation line 69";
        f = msgbox(msg);
        error(msg);
    otherwise
        display("You haven't made a choice." )
end



%% Superimpose potential flow functions

if ~exist('ANGLES', 'var') %Just one layer printed, angles are defined by the matrix W already 
    W_tot = W; % Here you can also superimpose. Try W_tot = W_cardio + W_vortex
    U0 = 0 ; 
    V0 = 0; 
    U = real(W_tot) + U0; 
    V = -imag(W_tot) + V0; 
    % Visualization 
    [l,s] = plotStreamlines(X,Y,U,V); 

    if strcmp(example,'The Starry Night')||strcmp(example,'Wood')
        I = imread(imgName);
        h = image(xlim,-ylim,I); 
        uistack(h,'bottom')
        set(l,'LineWidth',0.75)
        set(l,'Color','w')
        set(s,'Visible', "off");
    end

else %several layers, built in the struct ANGLES
    for i = 1:length(ANGLES)
        figure;
        title("Layer" + " " + num2str(i)); 
        plotFrame(imgName,dimx,dimy,resizeImg);
        [l,~] = plotStreamlines(ANGLES(i).X,ANGLES(i).Y,ANGLES(i).U,ANGLES(i).V); 
    end
end

title(example)

%% Save ANGLE & DIM values

if strcmpi(save_matlabfiles, 'yes')
    if ~exist(foldername, 'dir')
         mkdir(foldername)
    end
    
    if ~exist('ANGLES', 'var')
        ANGLES = struct('X','Y','U','V');
        ANGLES.X = X; 
        ANGLES.Y = Y; 
        ANGLES.U = U; 
        ANGLES.V = V; 
    end 

    save(strcat(foldername, 'ANGLES'), 'ANGLES');
    dim = [dimx dimy];
    save(strcat(foldername, 'DIM'),"dim"); 
end



%% SHAPE & EXAMPLE FUNCTIONS
function W_swirl = swirl(Z,S,V,Z0)

    W_swirl = (-S+1i*V)./(2*pi.*(Z-Z0));
end

function [dimx, dimy, Xchair,Ychair,W_chair] = chairExample()
    %Dimensional parameters
    LegLength = 40; %mm
    dimy = LegLength*(1+sqrt(2)); 
    dimx = LegLength*(2+sqrt(2)/2);
    centerSeat = -dimx/2 + LegLength*3/2; 

    %setup grid 
    Nx = floor(dimx); %number of points in x
    Ny = floor(dimy); %40; %15;
    x = linspace(-dimx/2,dimx/2,Nx);
    y = linspace(-dimy/2,dimy/2,Ny);
    [Xchair,Ychair] = meshgrid(x,y);
    Z = Xchair + 1i.*Ychair ; 

    
    %center of chair 
    W_swirl1 = swirl(Z, 1,3,centerSeat); 
    W_swirl1 = InfluenceRestrict(Xchair,Ychair,W_swirl1,LegLength/2,centerSeat,2,false);
    
    %Legs
    W_radial = swirl(Z, 1,0,centerSeat); 
    
    %total
    W_chair = W_radial + 5*W_swirl1; 
end

function [dimx, dimy, X,Y,ANGLES] = payloadadaptorExample()
    
    dimy = 1088/12; 
    dimx = 1828/12;

    %setup grid 
    Nx = floor(dimx); %number of points in x
    Ny = floor(dimy); %40; %15;
    x = linspace(-dimx/2,dimx/2,Nx);
    y = linspace(-dimy/2,dimy/2,Ny);
    [X,Y] = meshgrid(x,y);

     
    a = 1; 
    lambda = dimy/6;
    W_tot = a*(sin(X./lambda) + 1i*sin(Y./lambda)); 
    
    U0 = 0; 
    V0 = 0; 
    
    U = real(W_tot) + U0; 
    V = -imag(W_tot) + V0; 
    
    ANGLES = struct('X','Y','U','V');
    i = 1;
        ANGLES(i).X = X; 
        ANGLES(i).Y = Y; 
        ANGLES(i).U = U; 
        ANGLES(i).V = V; 
    i = 2;
        ANGLES(i).X = X; 
        ANGLES(i).Y = Y; 
        ANGLES(i).U = -V; 
        ANGLES(i).V = U; 

end

function [dimx, dimy, X,Y,W_tot] = starrynightExample()
    %initialize grid
    pts = 50; 
    Nx = 3*pts; %number of points in x
    Ny = pts; %15;
    dimx = 3*30; 
    dimy = 30;
    x = linspace(-dimx/2,dimx/2,Nx);
    y = linspace(-dimy/2,dimy/2,Ny);
    [X,Y] = meshgrid(x,y);
    Z = X + 1i.*Y ; 

    %major vortices
    z22 = 2.8-2.07i; 
    z1 = 17.832 - 7.88i; 
    W_swirl1 = swirl(Z,5,10,z1);
    W_swirl1 = InfluenceRestrictEllipse(X,Y,W_swirl1, 7.5, 12.15-9.83i,2,15,6) ;

    z21= -2 -1.13i;
    W_swirl21 =swirl(Z,-5,-12,z21); 
    W_swirl21 = InfluenceRestrict(X,Y,W_swirl21 ,7, -4.29-4.68i,10,0) ; %big one

    z22 = 2.8-2.07i;
    W_swirl22 =swirl(Z,10,10,z22); 
    W_swirl22 = InfluenceRestrict(X,Y,W_swirl22 , 8, z22+4i+1,10,0) ; 

    %top left corner detail
    Z_tl = -35 + 13i;
    G = -100;
    W_vortexTL = (1i*G+2)./(2*pi.*(Z-Z_tl));

    %bottom middle corner detail
    Z_bl = -12.7 -10i;
    G = +50;
    W_vortexBL = 1i*G./(2*pi.*(Z-Z_bl));
    W_vortexBL = InfluenceRestrict(X,Y,W_vortexBL, 4, Z_bl,3,0) ;

    %right moon
    Z_r = 38.1 + 6.75i;%34.3 + 6.6i; %40 +7i;
    G = -120;
    W_vortexR = 1i*G./(2*pi.*(Z-Z_r));


    %smaller ones, clocwise from top in a spiral
    z3 = -23.5+13.6i;
    z4 = -13.7 +13.4i; 
    z5 = -7.38 + 11.77i;
    z6 = 10.78 + 11i; 
    z7 = 19.7 + 3.77i;
    z8 = -32.9 -8.46i;
    z9 = -40.7 - 7.316i; 
    z10 = -23.28 + 6.4i ; 
    z12 = -15.2 - 0.68i;

    z_small = [z3 z4 z5 z6 z7 z8 z9 z10 z12];
    W_Small = zeros(size(X,1),size(X,2));  
    sign = ones(length(z_small),1);
    sign(6) = -1; sign(2) = -1; sign(end) = -1; sign(3) = -1; sign(4)= -1;
    rad = [3 3.5 4 4.5 5 3 3 2.5 1];

    for i=1:length(z_small)    
        W_swirl = swirl(Z,-10,sign(i)*75,z_small(i));
        W_swirl = InfluenceRestrict(X,Y,W_swirl, rad(i), z_small(i),10,0) ;
        W_Small = W_Small + W_swirl; 
    end

    W_tot =  100*W_swirl1 + 200*W_swirl21 + 100*W_swirl22 + 20*W_vortexTL + 20*W_vortexBL + 20*W_vortexR + 20*W_Small; 


%     U = real(W_tot); 
%     V = -imag(W_tot); 
%     figure()
% 
%     hold on;
%     seedpts = [z1 z10 z12 z21 z22 z3 z4 z5 z6 z7 z8 z9 Z_bl z_small Z_tl Z_r]; 

% 
%  l = streamslice(X,Y,U,V,5, 'noarrows', 'cubic');
%  set(l,'LineWidth',0.75)
%  set(l,'Color','w');
% axis equal
%  box on
% set(gca, 'FontName', 'Myriad Pro')
% set(gca,'XColor', 'none','YColor','none', 'color', 'none')
% % set(gca, 'color', 'none')
% 
% axis tight; 
% % scatter(real(Z),imag(Z), '.w')
% scatter(real(seedpts), imag(seedpts),50,'r.')
% 
% 



end

function [dimx, dimy,X,Y,W_tot] = woodExample()
    %Initialize grid
    Nx = 60; %number of points in x
    Ny = 40; 
    dimx = 60; 
    dimy = 40;
    x = linspace(-dimx/2,dimx/2,Nx);
    y = linspace(-dimy/2,dimy/2,Ny);
    
    [X,Y] = meshgrid(x,y);
    [Theta, ~] = cart2pol(X,Y);
    Z = X + 1i.*Y ; 
    
    %vortex
    z1 = -11.56 -8.11i;
    W_swirl1 = swirl(Z,4,50,z1); 
    zc = -5.8 - 8.14i; 
    W_swirl1 = InfluenceRestrictEllipse(X,Y,W_swirl1,zc,3,22,15, false);
    
    z2 = -13.81 + 7.32i;
    W_swirl2 = swirl(Z,-10,-20,z2); 
    W_swirl2 = InfluenceRestrictEllipse(X,Y,W_swirl2,z2,3,10,5, false);
    
    z3 = 9.72 + 11.35i;
    W_swirl3 = swirl(Z,-5,-60,z3); 
    zc2 = 3.79 + 8.34i; 
    W_swirl3 = InfluenceRestrictEllipse(X,Y,W_swirl3,zc2,3,17,28, false);
    
    %background uniform direction 
    a= 3.5;
    theta0 = cart2pol(-4.78,-9.39);
    U0 = -4 - a*cos(Theta+theta0) ; 
    V0 =-10- a*sin(Theta+theta0); 

    %superposition of fields    
    W_tot =40*W_swirl1 + 20*W_swirl2 + 5*W_swirl3 + U0 -1i.*V0; 

end
%% AUXILLIARY FUNCTIONS
function [l,s] = plotStreamlines(X,Y,U,V)
    s = scatter(X,Y, 3,[1, 1, 1].*0.8,'filled','o'); % 3,[1, 1, 1].*255/255,'.','filled')
    hold on
    l = streamslice(X,Y,U,V,5, 'arrows', 'cubic');
    set(l,'LineWidth',1)
    set(l,'Color','k'); %,'k'); % 238,238,228
    set(gca,'XColor', 'none','YColor','none', 'color', 'none')
    axis tight; axis equal
end

function plotFrame(imgName,dimx,dimy,varargin)
    %  --- what is a good image? --- %
    % B&W, no transparency, White = what is printed, and there should be at 
    % least 1 pixel of black all around
    hold on;    
    I = imread(imgName);
    binaryImage = rgb2gray(I)./255; 
    [B, ~, N] = bwboundaries(binaryImage);
    Ix = size(I,2); Iy = size(I,1); 

    %optional argument of rescaling 
    p = inputParser; 
    default_rescalesize =  min(Ix/dimx,Iy/dimy);
    validationFcn = @(x) isnumeric(x) && isscalar(x) && (x > 0);
    addOptional(p,'sz_rescale',default_rescalesize,validationFcn);
    parse(p,varargin{:});
    
    sz_rscale = p.Results.sz_rescale;

    colorOutline = [95,2,31]./255; 
    for k=1:length(B)
       boundary = B{k};
       if(k > N)
         plot(boundary(:,2)./sz_rscale - dimx/2, -(boundary(:,1)./sz_rscale - dimy/2), 'Color',flip(colorOutline),'LineWidth',2);
       else
         plot(boundary(:,2)./sz_rscale - dimx/2, -(boundary(:,1)./sz_rscale- dimy/2), 'Color',colorOutline,'LineWidth',2);
       end
    end
end

% function [W_infl,Dist] = InfluenceRestrict(X,Y,W,R,Z0,Rfall,boolPlot)
%     % aim: make zeros all points of W outside the circle defined by center Z0 and
%     % radius R
% %     X = real(W); Y = imag(W); 
%     X0 = real(Z0) ;  Y0 = imag(Z0);
%     Dist = sqrt((X - X0).^2 + (Y - Y0).^2);
%     mask = Dist<R; 
%     meanfiltersize = 3; %floor(R/3); 
%     mask_smooth = smooth2a(mask,meanfiltersize); %size (2*Nr+1)-by-(2*Nc+1)
%     if boolPlot == true
%         figure;
%         set(gca,'YDir','normal')
%         imshow(mask_smooth);
%         figure; axis equal
%     end
%     W_infl = W.*mask_smooth;
% end


function [W_infl,Dist] = InfluenceRestrict(X,Y,W,R,Z0,Rfall,bool)
    % aim: make zeros all points of W outside the circle defined by center Z0 and
    % radius R
%     X = real(W); Y = imag(W); 
    X0 = real(Z0) ;  Y0 = imag(Z0);
    Dist = sqrt((X - X0).^2 + (Y - Y0).^2);
    mask = Dist<R; 
    mask_smooth = smooth2a(mask,floor(R/Rfall));
    if bool == true
        imshow(mask_smooth);
    end
    W_infl = W.*mask_smooth;
end

function [W_infl,Dist] = InfluenceRestrictEllipse(X,Y,W,R,Z0,Rfall,a,b)
    % aim: make zeros all points of W outside the circle defined by center Z0 and
    % radius R STARRY NIGHT

    X0 = real(Z0) ;  Y0 = imag(Z0);
    Dist = sqrt(((X - X0)./a).^2 + ((Y - Y0)./b).^2);
    mask = Dist<1; 

    mask_smooth = smooth2a(mask,floor(R/Rfall));
%         imshow(mask_smooth)
    W_infl = W.*mask_smooth;
end


% function [W_infl,Dist] = InfluenceRestrictEllipse(X,Y,W,Z0,Rfall,a,b, bool)
%     % aim: make zeros all points of W outside the circle defined by center Z0 and
%     % radius R
% 
%     X0 = real(Z0) ;  Y0 = imag(Z0);
%     Dist = sqrt(((X - X0)./a).^2 + ((Y - Y0)./b).^2);
%     mask = Dist<1; 
%     R = sqrt(a*b);
%     mask_smooth = smooth2a(mask,floor(R/Rfall));
%     if bool == true
%         imshow(mask_smooth);
%     end
%     W_infl = W.*mask_smooth;
% end

function matrixOut = smooth2a(matrixIn,Nr,Nc)
% Smooths 2D array data.  Ignores NaN's.
%
%function matrixOut = smooth2a(matrixIn,Nr,Nc)
% 
% This function smooths the data in matrixIn using a mean filter over a
% rectangle of size (2*Nr+1)-by-(2*Nc+1).  Basically, you end up replacing
% element "i" by the mean of the rectange centered on "i".  Any NaN
% elements are ignored in the averaging.  If element "i" is a NaN, then it
% will be preserved as NaN in the output.  At the edges of the matrix,
% where you cannot build a full rectangle, as much of the rectangle that
% fits on your matrix is used (similar to the default on Matlab's builtin
% function "smooth").
% 
% "matrixIn": original matrix
% "Nr": number of points used to smooth rows
% "Nc": number of points to smooth columns.  If not specified, Nc = Nr.
% 
% "matrixOut": smoothed version of original matrix
% 
% 
% 	Written by Greg Reeves, March 2009.
% 	Division of Biology
% 	Caltech
% 
% 	Inspired by "smooth2", written by Kelly Hilands, October 2004
% 	Applied Research Laboratory
% 	Penn State University
% 
% 	Developed from code written by Olof Liungman, 1997
% 	Dept. of Oceanography, Earth Sciences Centre
% 	G�teborg University, Sweden
% 	E-mail: olof.liungman@oce.gu.se
%
% Initial error statements and definitions
%
if nargin < 2, error('Not enough input arguments!'), end
N(1) = Nr; 
if nargin < 3, N(2) = N(1); else N(2) = Nc; end
if length(N(1)) ~= 1, error('Nr must be a scalar!'), end
if length(N(2)) ~= 1, error('Nc must be a scalar!'), end
%
% Building matrices that will compute running sums.  The left-matrix, eL,
% smooths along the rows.  The right-matrix, eR, smooths along the
% columns.  You end up replacing element "i" by the mean of a (2*Nr+1)-by- 
% (2*Nc+1) rectangle centered on element "i".
%
[row,col] = size(matrixIn);
eL = spdiags(ones(row,2*N(1)+1),(-N(1):N(1)),row,row);
eR = spdiags(ones(col,2*N(2)+1),(-N(2):N(2)),col,col);
%
% Setting all "NaN" elements of "matrixIn" to zero so that these will not
% affect the summation.  (If this isn't done, any sum that includes a NaN
% will also become NaN.)
%
A = isnan(matrixIn);
matrixIn(A) = 0;
%
% For each element, we have to count how many non-NaN elements went into
% the sums.  This is so we can divide by that number to get a mean.  We use
% the same matrices to do this (ie, "eL" and "eR").
%
nrmlize = eL*(~A)*eR;
nrmlize(A) = NaN;
%
% Actually taking the mean.
%
matrixOut = eL*matrixIn*eR;
matrixOut = matrixOut./nrmlize;

end