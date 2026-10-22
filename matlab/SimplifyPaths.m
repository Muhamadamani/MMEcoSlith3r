function Simpllayer = SimplifyPaths(layer, prtOpt,pltOpt)

    if strcmp(prtOpt.ControlSeedPoint, 'yes') %regular straighlines are expected then, give less importance to distance interpolation 
        prtOpt.distInterp = 50;
    end
    idealDistSpacing = prtOpt.upperbound/2; 
    numCourse_mem  = 0; 

    nLayer = length(layer);
         for numLayer = 1:nLayer
             ncourses = size(layer(numLayer).Course,2);
             numCourse_mem  = 1; 
            for numCourse = 1:ncourses
                
                x = layer(numLayer).Course(numCourse).POINT(:,1) ;
                y = layer(numLayer).Course(numCourse).POINT(:,2) ;
                width = layer(numLayer).Course(numCourse).POINT(:,4);
                if length(x)>1 %skip the course if it's only one single point
                    pol = [x y width];
            
                    [ps, ix] = dpsimplify(pol,prtOpt.tol) ; %simplication according to Douglas-Peucker algorithm
                    
                    % Interpolation for linear segments 
                    diffps = diff(ps,1,1); 
                    DistPoints =  (sqrt( diffps(:,1).^2 + diffps(:,2).^2 ) ); 
            
                    idW = find(diffps(:,3)>prtOpt.widthInterp); %find index of segments whose width is larger than widthInterp
                    idD = find(DistPoints>prtOpt.distInterp);%find index of segments whose distance is larger than distInterp
                    id = unique(sort([idW; idD],"ascend")); %gather all problematic segments
                    mem_shift = 0; %keeps track of offset that builds up as new segments are added
    
                    if ~isempty(id) 
                        for i = 1:length(id)
                            idi = id(i);
                            Npoints = ceil(DistPoints(idi)/idealDistSpacing);
                            if Npoints<2 %case where the distance is very small (so width is varying a lot)
                                Npoints = 3; 
                            end
                            idi = idi + mem_shift;
                            pt = evenLinear(Npoints,ps(idi:idi+1,1),ps(idi:idi+1,2), ps(idi:idi+1,3));
                            ps = [ps(1:idi-1,:);pt;ps(idi+2:end,:)]; 
                            mem_shift = mem_shift + Npoints-2; 
                        end
                    end
    
                    height = prtOpt.layer_height*ones(size(ps,1),1)*numLayer;
                    leanlayer(numLayer).Course(numCourse_mem).POINT = [ps(:,1),ps(:,2), height,ps(:,3)]; 
                    
                    numCourse_mem= numCourse_mem+1; 
    
                    if strcmpi(pltOpt.plot_curvesimplification, 'yes')&&ismember(numCourse, [1:7])
                        %this limits the amount of curves to look at 
                        figure()
                        plot3(x,y,width, ':r','LineWidth', 2);      
                        hold on 
                        plot3(ps(:,1),ps(:,2),ps(:,3),'ko-');
                        title(sprintf('Point Reduction from %d to %d', size(pol,1), size(ps,1))); 
                    end 
                end
            end
         end

     if prtOpt.boolFilter == 1 %Remove points shorter than threshDist
        for layer_num = 1:nLayer
        
            ncourses = size(leanlayer(layer_num).Course,2);
            course_stack_id = 1;
        
            for course_num = 1:ncourses
                %calculate total distance of that course
                dx = diff(leanlayer(layer_num).Course(course_num).POINT(:,1) ); 
                dy = diff(leanlayer(layer_num).Course(course_num).POINT(:,2) ); 
                distVertice = sum(sqrt(dx.^2 + dy.^2)); 
        
                if (distVertice>prtOpt.threshDist) %if too small of a distance: ignore, don't add up
                    Simpllayer(layer_num).Course(course_stack_id).POINT(:,1) = leanlayer(layer_num).Course(course_num).POINT(:,1) ; 
                    Simpllayer(layer_num).Course(course_stack_id).POINT(:,2) = leanlayer(layer_num).Course(course_num).POINT(:,2) ; 
                    Simpllayer(layer_num).Course(course_stack_id).POINT(:,3) =  leanlayer(layer_num).Course(course_num).POINT(:,3);
                    Simpllayer(layer_num).Course(course_stack_id).POINT(:,4) =  leanlayer(layer_num).Course(course_num).POINT(:,4);
                    course_stack_id = course_stack_id+1 ;
                end
            end
        end

     else Simpllayer = leanlayer;
     end
end

 function pt = evenLinear(NbPoints,x,y,z)
   %creates evenly-spaced coordinates vector of size NbPoints-3 in between
   %bounds set by x,y,z. x,y,z must be 2x1 vectors.
   xLin = linspace(x(1),x(2),NbPoints);
   yLin = linspace(y(1),y(2),NbPoints);
   zLin = linspace(z(1),z(2),NbPoints);

   pt = [xLin' yLin' zLin'];
 end


