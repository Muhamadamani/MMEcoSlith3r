function layerTrim = CutShape(layer, ANGLES, dim, prtOpt) 
   
binaryImage = rgb2gray(prtOpt.I)./255; 
    [B, ~, ~] = bwboundaries(binaryImage); 
    
    Ix = size(prtOpt.I,2); Iy = size(prtOpt.I,1); 
    
    sz_rscale =  min(Ix/dim(1),Iy/dim(2)); %mean of the two scales up
    boundary = B{1}; %needs adaptation for a more complex shape
    boundary_scale = [boundary(:,2)./(Ix/dim(1)) - dim(1)/2 boundary(:,1)./(Iy/dim(2)) - dim(2)/2]; 
     
    Ix = size(binaryImage,2); Iy = size(binaryImage,1); 
    nLayer = length(ANGLES);

for numLayer = 1:nLayer
    X = ANGLES(numLayer).X; Y = ANGLES(numLayer).Y; 
    minx = min(X,[],"all");          miny = min(Y,[],"all");       
    Lx = max(X,[],"all") - minx;     Ly = max(Y,[],"all") - miny;

     ncourses = size(layer(numLayer).Course,2);
     mem_course = 0; 
    for numCourse = 1:ncourses
        
        x = layer(numLayer).Course(numCourse).POINT(:,1) ;
        y = layer(numLayer).Course(numCourse).POINT(:,2) ;
        width = layer(numLayer).Course(numCourse).POINT(:,4) ;
        
        xIm = floor( Ix/Lx.*x  + Ix/2) +1; 
        %floor(x*sz_rscale) + floor(Ix/2);
        yIm = floor( Iy/Ly.*y  + Iy/2) +1 ;  %floor(y*sz_rscale) + floor(Iy/2); 
        
        % %% new mu
        % xIm = min(max(xIm, 1), Ix);
        % yIm = min(max(yIm, 1), Iy);
        % 
        % % end mu
        xnew = [];   ynew = []; widthnew = []; 
        
        previousfilled = false; %flag to check interruptions
        previousfilled_mem = 0; 

        for iPt = 1:length(x) %iterate through 
            mask = binaryImage(yIm(iPt), xIm(iPt)); 
            if (mask==1) %if the corresponding element should be filled -> add point to course 
                xnew = [xnew; x(iPt)];
                ynew = [ynew; y(iPt)];
                widthnew = [widthnew; width(iPt)];
                previousfilled = true;
            elseif (mask==0)&&(previousfilled == true) %we're seeing a first interruption
                xnew = [xnew; NaN];
                ynew = [ynew; NaN];
                widthnew = [widthnew; NaN];
                previousfilled_mem = previousfilled_mem +1 ; 
                previousfilled = false; %reset: next 0s shouldnt be seen as interruptions
            end
        end

        if ~isempty(xnew) %only add course to new struct if at least 1 point overlapped

            %NaNs should be interrupted courses, except when they're at the
            %end 
            interrupt = find(isnan(xnew)); 
            interrupt(interrupt == length(xnew)) = []; 
            lastix = 1; 

            if ~isempty(interrupt) %there's a NaN or more in middle of the course
                for iStop = 1:(length(interrupt)+1)

                    if iStop<=length(interrupt)
                         index_trim = lastix:interrupt(iStop)-1; 
                        lastix = interrupt(iStop)+1; %for next iter, start index +1 to avoid NaN
                    else
                        index_trim = lastix:length(xnew);
                    end

                    %save in struct & plot
                    if length(index_trim)>2 %make sure singletons are ignored
                        mem_course = mem_course+1; 
                        layerTrim(numLayer).Course(mem_course).POINT = [xnew(index_trim)  ...
                                        ynew(index_trim)  ones(length(index_trim),1) ...
                                        widthnew(index_trim) ]; 
                    end
%                     mem_course
%                    if mem_course == 98
%                        xnew
%                    end 
                end
            else %no interruption
                mem_course = mem_course+1; 
                layerTrim(numLayer).Course(mem_course).POINT = [xnew ynew ones(length(xnew),1) widthnew]; 
              

            end            
        end
    end 
    % Simplify last path which is the edge of the image, does not work with
    % holes yet
    pol = [boundary_scale(:,1) boundary_scale(:,2)] ;    
    polpoly = polyshape(pol);
    polyout = simplify(polpoly,'KeepCollinearPoints',false) ;
    [ps, ix] = dpsimplify(pol,prtOpt.tol*5) ;
    layerTrim(numLayer).Course(mem_course+1).POINT = [ps(:,1), ps(:,2), ones(size(ps,1),1), (prtOpt.upperbound/2)*ones(size(ps,1),1) ];

end 

end