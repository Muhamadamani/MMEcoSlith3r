function [xy,ic]=mmstream2(x,y,u,v,x0,y0,mark,step,Nmem)
% Duane Hanselman (2022). Improved 2-D Streamlines 
% (https://www.mathworks.com/matlabcentral/fileexchange/38860-improved-2-d-streamlines), 
% MATLAB Central File Exchange. Retrieved July 25, 2022.

%MMSTREAM2 Improved 2D Streamlines.
% XY = MMSTREAM2(X,Y,U,V,X0,Y0,Mark,Step) computes streamlines from gradient
% data in matrices U and V.
%
% X and Y can be vectors defining the coordinate axes data where U(i,j) and
% V(i,j) coincide with the coordinates axes points X(j) and Y(i).
% Alternatively, X and Y can be 2D plaid matrices as produced by MESHGRID.
%
% X0 and Y0 are equal length vectors defining coordinates that mark the
% Start, End, or a point On individual streamlines as denoted by the input
% Mark which is 'Start', 'End' or 'On'. If empty or not given Mark='Start'.
%
% Step identifies the normalized step size used. If empty or not given,
% Step = 0.1, i.e., 1/10 of a cell. 0.01 <= Step <= 0.5

% Nmem is the number of iterations over which we detect the presence of change 
% to avoid being trapped in a singularities (especially Vortex).
% if after Nmem iteration the total amount of new cells covered is less than 5, the
% streamline is ended. Default value is 1000, but in the presence of vortex
% the recommended value is 100. This means that the trapped region of a streamline would be
% Nmem waypoints long at max. 

%
% XY is a cell array containing streamline data points. XY{k}(:,1) contains
% the x-axis data and XY{k}(:,2) contains the y-axis data for the k-th
% streamline.
% ic is a boolean indicating if the streamline was closed (true if that's
% the case)
%
% Improvements over MATLAB's STREAM2:
% Will find closed streamlines.
% Will selectively go downstream, upstream, or both directions from a point.
% Uses a more accurate integration routine.
% X and Y need not linearly spaced.
%
% STREAMLINE(XY) plots the streamlines on the current axes.
% D.C. Hanselman, University of Maine, Orono, ME 04469
% MasteringMatlab@yahoo.com
% Mastering MATLAB 7
% 2005-06-21
% Revised 2005-08-31, 2007-07-03, 2008-07-29
if nargin<9 || isempty(step)                        % parse input arguments
   step=0.1;
end
if nargin<8 || isempty(Nmem)                        % parse input arguments
   Nmem=1000;
end
if nargin<7 || isempty(mark)
   mark='start';
end
if nargin<6
   error('At Least Six Input Arguments are Required.')
end
if ~isnumeric(step) || numel(step)>1 || step<0.01 || step>0.5
   error('Step Must be a Scalar Between 0.01 and 0.5')
end
if ~isnumeric(Nmem) || mod(Nmem,1) ~= 0 || numel(Nmem)>1 || Nmem<10
   error('Nmem Must be a Integer above 10')
end
if ~ischar(mark) || ~any(lower(mark(1))=='seo')
   error('Mark Must be ''Start'', ''End'', or ''On''')
end
mark=lower(mark(1));
if any(size(u)~=size(v))
   error('U and V Must be the Same Size.')
end
if ndims(u)~=2 || min(size(u))<2
   error('U and V Must be 2D and at Least 2-by-2.')
end
if all(size(x)==size(y)) && min(size(x))>1 % x and y are plaid
   xx=x;                  % save plaid
   yy=y;
   x=x(1,:)';             % create axes vectors
   y=y(:,1);
else                                       % x and y are axes vectors
   x=x(:);                % save axes vectors
   y=y(:);
   [xx,yy]=meshgrid(x,y); % create plaid
end
if any(abs(diff(x))<eps) || any(abs(diff(y))<eps)
   error('X and Y Must Not Have Consecutive Equal Values.')
end
Nx=length(x);
Ny=length(y);
if Nx~=size(u,2)
   error('X Must Have as Many Elements or Columns as U and V Have Columns.')
end
if Ny~=size(u,1)
   error('Y Must Have as Many Elements or Rows as U and V Have Rows.')
end
x0=x0(:);
y0=y0(:);
N0=length(x0);
% ic = false; 
if N0~=length(y0)
   error('X0 and Y0 Must Contain the Same Number of Elements.')
end

xy=cell(1,N0); % create cells for output
for k=1:N0 % find streamlines given [x0, y0] pairs
   
   if x0(k)<min(x) || x0(k)>max(x) ||...
      y0(k)<min(y) || y0(k)>max(y)   % point is outside map
      continue %go to the next starting point
   end
   % figure out what cell [x0,y0] is in
   [idx,idx]=min(abs(x0(k)-xx(:))+abs(y0(k)-yy(:)));
   [i,j]=ind2sub(size(u),idx); %[I,J] = ind2sub(SIZ,IND) returns the arrays I and J containing the equivalent row and column subscripts corresponding to the index matrix IND for a matrix of size SIZ.  
   if j==1 %left edge
      jlim=[j j+1];
   elseif j==Nx %right edge
      jlim=[j-1 j];
   elseif abs(x0(k)-x(j-1))<abs(x0(k)-x(j+1)) %closer to the cell in j-1 than to that of j+1
      jlim=[j-1 j];
   else
      jlim=[j j+1];
   end
   if i==1
      ilim=[i i+1];
   elseif i==Ny
      ilim=[i-1 i];
   elseif abs(y0(k)-y(i-1))<abs(y0(k)-y(i+1))
      ilim=[i-1 i];
   else
      ilim=[i i+1];
   end
   switch mark
   case 's'
      [xy{k},ic]=local_getstream(x,y,u,v,ilim,jlim,x0(k),y0(k),step,Nmem);
   case 'e'
     [xy{k},ic]=local_getstream(x,y,-u,-v,ilim,jlim,x0(k),y0(k),step,Nmem);
     [xy{k},ic]=xy{k}(end:-1:1,:); % make stream flow downhillm
   case 'o'
      [xy{k},ic]=local_getstream(x,y,u,v,ilim,jlim,x0(k),y0(k),step,Nmem);
      if ~ic % go other direction only if streamline is not closed
         xye=local_getstream(x,y,-u,-v,ilim,jlim,x0(k),y0(k),step,Nmem);
         xy{k}=[xye(end:-1:2,:);xy{k}]; % make stream flows downhill
      end
   end
end
end
%--------------------------------------------------------------------------
%--------------------------------------------------------------------------
function [xy,ic]=local_getstream(x,y,u,v,ilim,jlim,x0,y0,step, Nmem)
% move from cell to cell gathering a streamline
% xy is a double array
% ic is true if streamline is closed
ic=false;    % logical variable that is true if streamline is closed
xy0=[x0 y0]; % hold starting point so that closed streamlines can be found
xy=zeros(1000,2); % allocate storage
k=1; % pointer to next index to store data
kglob = 1; %store how much time the loop has been called  

% Nmem = 10; %50; 
memjlim = 1000*rand([Nmem,2]); memilim = 1000*rand([Nmem,2]); %store the 100 last jlim and ilim to check if we're endlessly in a small spiral ; use random to avoid a pattern in the beginning 

while true
   xlim=x(jlim);
   ylim=y(ilim);
   ulim=u(ilim,jlim);
   vlim=v(ilim,jlim);
   [dxy,ii,jj]=local_cellstream(xlim,ylim,ulim,vlim,x0,y0,xy0,step, kglob);
   np=size(dxy,1);
   if k+np-1>size(xy,1)   % allocate more storage if needed
      xy=[xy;zeros(500,2)];%#ok
   end
   xy(k:k+np-1,:)=dxy; % poke data into storage array
   k=k+np;             % update pointer
   jlim=jlim+jj;
   ilim=ilim+ii;
   
   memilim(end+1,:) = ilim;  memilim = memilim(2:end,:); %update to keep only last record
   memjlim(end+1,:) = jlim;  memjlim = memjlim(2:end,:); 

   totchange = sum(max(abs(diff(memilim)))+max(abs(diff(memjlim)))); 
    
   if jlim(1)<1 || jlim(2)>length(x) || ... %meeting edges
      ilim(1)<1 || ilim(2)>length(y)
      xy(k-1:end,:)=[]; % throw away unused storage
      break
   elseif (ii==0 && jj==0) || np==0 %not adding anything, staying within the cell 
      xy(k:end,:)=[]; % throw away unused storage
      if ~isempty(xy)
        ic=isequal(xy(end,:),xy0); 
      else
          disp('Empty streamline here')
          ic = 0; 
      end
      break
   elseif abs(totchange)<=5 %over 100 iteration the cells have not moved more than 5: singularity
       xy(k:end,:)=[]; % throw away unused storage
%        disp('out!'); 
       break
   end
   x0=dxy(end,1); %new start point = end of newly found streamline 
   y0=dxy(end,2);
   kglob = kglob+1;
end
end
%--------------------------------------------------------------------------
function [xy,ii,jj,ic]=local_cellstream(xlim,ylim,ulim,vlim,x0,y0,xy0,step,kglob)
% starting at the point [sx, sy] create a streamline until the edge of the
% cell given by xlim and ylim is reached.
%
% xlim = [x1 x2]                ylim = [y1 y2]
%
% ulim = [u(x1,y1) u(x2,y1)     vlim = [v(x1,y1) v(x2,y1)
%         u(x1,y2) u(x2,y2)];           v(x1,y2) v(x2,y2)];
xymin=[xlim(1) ylim(1)]; % [x1 y1]
xymax=[xlim(2) ylim(2)]; % [x2 y2]
xybox=xymax-xymin;       % [x2-x1 y2-y1]
uv=[ulim(:) vlim(:)]';   % [u(x1,y1) u(x1,y2) u(x2,y1) u(x2,y2);
                         %  v(x1,y1) v(x1,y2) v(x2,y1) v(x2,y2)];
tol=1e-4;
N=round(3/step);
xy=zeros(N,2); % preallocate memory for result
cstep=1.5*step;% step size for closed streamline detection
k=1;
xy(k,:)=[x0 y0]; % first point
ii=0;            % next cell in x
jj=0;            % and y direction

ic = false; 
timeLimit = 10; %10s per loop max
time0 = tic;
% scatter(x0,y0, 'k')
%  hold on
while true || toc(time0)<timeLimit
   abk=(xy(k,:)-xymin)./xybox; % normalized current position [alpha beta]
   % compute slopes at current point      
   uvk=((1-abk(1))*( (1-abk(2))*uv(:,1) + abk(2)*uv(:,2)) + ...
           abk(1) *( (1-abk(2))*uv(:,3) + abk(2)*uv(:,4)))';      % [uk vk]
       
   if k>1 && max(abs(uvk))<tol  % at minimum, this stream stops
      xy(k+1:end,:)=[];
      break
   end
   
   h=min(step*abs(xybox)./(max(abs(uvk),tol)));       % allowable step size   
   
   xy(k+1,:)=xy(k,:) + h*uvk;                    % Forward Euler Prediction
   
   abi=(xy(k+1,:)-xymin)./xybox;        % normalized position at next point
   uvi=((1-abi(1))*( (1-abi(2))*uv(:,1) + abi(2)*uv(:,2)) + ...
           abi(1) *( (1-abi(2))*uv(:,3) + abi(2)*uv(:,4)))';      % [ui vi]
        
   xy(k+1,:)=xy(k,:) + h*(uvk + uvi)/2;       % Trapezoidal Rule Correction
   k=k+1;
   
   if k>2 && norm((xy(k,:)-xy(k-2,:))./xybox,inf)<step/2% stuck inside cell
      xy(k-2:end,:)=[];
      break
   elseif k>=2 && kglob>1 && norm((xy(k,:)-xy0)./xybox,inf)>0 && norm((xy(k,:)-xy0)./xybox,inf)<=cstep   % closed streamline
      scatter(xy(k,1), xy(k,2), 'r');
       xy(k,:)=xy0; % close the streamline
      xy(k+1:end,:)=[];
      ic = true; 
      scatter(x0,y0, 'k');  scatter(xy0(1,1), xy0(1,2), 'g');
      break
   elseif k==N+1                                        % stuck inside cell
      break
   else                                       % check if moved outside cell
      
      jj=sign(xybox(1))*(-(xy(k,1)<xlim(1)) + (xy(k,1)>xlim(2)));
      ii=sign(xybox(2))*(-(xy(k,2)<ylim(1)) + (xy(k,2)>ylim(2)));
      if jj~=0 || ii~=0                                % point to next cell
         xy(k+1:end,:)=[];
         break
      end
   end
%     scatter(xy(k,1), xy(k,2), 'r')
end
end

%{ 
 Copyright (c) 2008, Duane Hanselman
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
%}