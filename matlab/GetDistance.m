function [d_average,lines] = GetDistance(lines,i,PrtOpt)
% retrieves distance between lines{i} and closest 2 other neighbouring lines 
    if strcmp(PrtOpt.Spirals, 'yes') 
        %lines = correctSpiralCurvature(lines,i);
        lines = correctSpiralDensity(lines,i);
        %lines = correctSpiralGraph(lines,i);
        %lines = correctSpiralOlder(lines,i);
    end

    %all lines but lines{i}
    verts1 = vertcat(lines{1:i-1});
    verts1 = [verts1; vertcat(lines{i+1:length(lines)})];

    td = delaunayTriangulation(verts1);
    [pl1,d1] = nearestNeighbor(td, lines{i}(:,1:2));


    % pop out these closest points from verts
    verts2 = setdiff(verts1, verts1(pl1, :), 'rows');
    td2 = delaunayTriangulation(verts2);
    [pl2, d2] = nearestNeighbor(td2, lines{i}(:,1:2));

    %result is averaged out (we assume that melt will flow in the middle
    %evenly)
    d_average = (d1+d2)/2;
        
    % look for eventual outliers 
    idx = find(d_average>PrtOpt.upperbound); 
    d_average(idx)  = min(d1(idx),d2(idx)); 
    idx2 = find(d_average>PrtOpt.upperbound);  %do a second check, might be that both neighbours are above bandwdith!
    d_average(idx2)  = PrtOpt.upperbound; 
%     colrange = 10*d_average/abs(max(d2) - min(d2));
    
    
end


 function [vert,dist] = correctSpiral(spiral,bandwidth)
     tself = delaunayTriangulation(spiral); %triplot(tself)
%     C = convexHull(tself); 
%     center=mean(spiral); %(tself.Points(C,:));
    
    
    %Step2; intersect the curve in multiple segments, with the line linking center of spiral to
    %start point ; we want 2 intersection lines perpendicular to each other to be able to 
    % mitigate edge effects
    CUT = [spiral(end,1) spiral(1,1); %x
            spiral(end,2) spiral(1,2)]; %y

    vCUT = [spiral(1,1) - spiral(end,1); spiral(1,2) - spiral(end,2)]; %director vector 
    nCUT = [vCUT(2); -vCUT(1)]; %its normal ; will be useful for 

     plot(CUT(1,:),CUT(2,:), 'r-')

    CUT2 = [spiral(end,1) spiral(end,1)+nCUT(1); 
        spiral(end,2) spiral(end,2)+nCUT(2)]; 
%     plot(CUT2(1,:),CUT2(2,:), 'r-')
     
    [xP,yP] = polyxpoly(spiral(:,1),spiral(:,2),CUT(1,:),CUT(2,:)) ; %(spiral,CUT);
%     scatter(xP,yP,30, 'k','filled', 'o');

    [xN,yN] = polyxpoly(spiral(:,1),spiral(:,2),CUT2(1,:),CUT2(2,:)) ; %(spiral,CUT);
    

    %Step 3; split the curve accordingly by finding nearest point to each intersection
    %and segmenting the curve;
    inter{1} = [xP,yP];
    inter{2} = [xN,yN];
    clear segment_ok
    clear dist_ok
    for j = 1:2 %repeat for the 2 intersection curves

        id = dsearchn(spiral,inter{j}); 
        x = spiral;
        y = [id(2:end); length(x)]'; %gather up all indices including end of x 
        segments = mat2cell(x(1:y(end),:),diff([0,y]),2);
        dist = segments; 
        
        %Step 4; Calculate distance with delaunay from 1 segments to the others
        for i=1:length(segments)
                verts1 = vertcat(segments{1:i-1});
                verts1 = [verts1; vertcat(segments{i+1:length(segments)})];
                
        %         verts1 = verts1'; 
                td = delaunayTriangulation(verts1);
                [pl1,d1] = nearestNeighbor(td, segments{i}(:,1:2));
        
        
                % pop out these closest points from verts
                verts2 = setdiff(verts1, verts1(pl1, :), 'rows');
                td2 = delaunayTriangulation(verts2);
                [pl2, d2] = nearestNeighbor(td2, segments{i}(:,1:2));
        
                d_average = (d1+d2)/2;
                dist{i} = d_average; 
        
            %Step 5; if distance happens to be too small, cull the segment
    	        if mean(d_average)<bandwidth/10
                    
                    break
                else 
%                     A = cell2mat(segments([1:i])); %segment_ok = cell2mat(segments([1:i]));
%                     segment_ok(:,:,j) = A; 
                    segment_ok{j} = cell2mat(segments([1:i]));
                     dist_ok{j} =cell2mat(dist([1:i]));
                end
        end

    end

%     S = segment_ok{1};
%     D= dist_ok{1};
    %Step 6; Compare the distances calculated: close to the intersections
    %there will be edge issues (neighbour point is considered closest); so
    %take the max of the 2 distances for the same point; 
   
    %first merge the values so that all points that have been culled by one
    %or the other disappear
    [vert,ia,ib] = intersect(segment_ok{1},segment_ok{2}, 'rows','stable'); %intersect(A,B) returns the data common to both A and B, with no repetitions. verts=C is in sorted order. Generally, C = A(ia) and C = B(ib).
    dist = max([dist_ok{1}(ia) dist_ok{2}(ib)],[],2); 

%                 axis equal
%             ps = plot(vert(:,1), vert(:,2), 'b.');
%             sz  = 20*dist; 
%             hold on
%             scatter(vert(:,1), vert(:,2), sz', dist');
%             ps.Visible = 'off';
%             colorbar()
%             figure; 
%      
 end

 function [lines] = correctSpiralCurvature(lines,i)
        % Here we check the curvature of each line and purge the values
        % which are larger than a threshold for a sustained period of time.

        differentiable = size(lines{i}(:,1))>4;
        if differentiable(1)==true
            x = lines{i}(:,1);
            y = lines{i}(:,2);
            % size 1 smaller due to diff
            x_dot = diff(x); 
            y_dot = diff(y);
            % size 2 smaller due to diff of diff
            x_dot_dot = diff(x_dot); 
            y_dot_dot = diff(y_dot);
            % warning: quadratically extrapolating to get equal sizes, maybe
            % padding would be more suitable
            x_dot_dot_dot = diff(x_dot_dot);
            x_dot_dot_dot_dot = diff(x_dot_dot_dot); % I know.
            y_dot_dot_dot = diff(y_dot_dot);
            y_dot_dot_dot_dot = diff(y_dot_dot_dot);
            x_dot_dot(end+1) = x_dot_dot(end)+x_dot_dot_dot(end)+x_dot_dot_dot_dot(end);
            x_dot_dot(end+1) = x_dot_dot(end)+x_dot_dot_dot(end)+2*x_dot_dot_dot_dot(end);
            y_dot_dot(end+1) = y_dot_dot(end)+y_dot_dot_dot(end)+y_dot_dot_dot_dot(end);
            y_dot_dot(end+1) = y_dot_dot(end)+y_dot_dot_dot(end)+2*y_dot_dot_dot_dot(end);
            % linearly for x,y dot
            x_dot(end+1) = x_dot(end)+x_dot_dot(end);
            y_dot(end+1) = y_dot(end)+x_dot_dot(end);
            
            signed_curvature=(x_dot.*y_dot_dot-y_dot.*x_dot_dot)./((x_dot.^2+y_dot_dot.^2).^(3/2));

    
            % MORE GENERAL CHECK, TODO: change these to arguments
            window_length = 20;
            curvature_threshold = 1/0.2;
    
            % SPIRAL ASSUMED ONLY AT ENDS
            averaged_curve = movmean(signed_curvature, window_length);
            if averaged_curve(1)>curvature_threshold
                i_start_of_normal = find(averaged_curve<curvature_threshold, 1);
                x(1:i_start_of_normal)=[];
                y(1:i_start_of_normal)=[];
                lines{i}=[x,y];
                figure();
                plot(signed_curvature);
            else
                flipped_average = movmean(flip(signed_curvature), window_length);
                if flipped_average(1)>curvature_threshold
                    i_end_of_normal = find(flipped_average<curvature_threshold, 1);
                    x(end-i_end_of_normal:end)=[];
                    y(end-i_end_of_normal:end)=[];
                    lines{i}=[x,y];
                    figure();
                    plot(signed_curvature);

                end
            end
        end
    %         find(signed_curvature<curvature_threshold, 1)
    %         mean_signed_curvature = movmean(signed_curvature, window_length); 
    %         lines{i}(find(mean_signed_curvature > curvature_threshold),1) = [];
    %         lines{i}(find(mean_signed_curvature > curvature_threshold),2) = []
 end
 function [lines] = correctSpiralDensity(lines,i)
        % Check density of points starting from endpoint and increasing
        % radius periodically, if density increases over a threshold we
        % process line to truncate endpoints

            % TODO: Change these to arguments
            minimum_points_for_spiral = 100;
            density_window = 0.2; % percentage of points close to the endpoints which are assumed to be spiral
            density_threshold = 1.1;
            truncation_percentage = 0.05;
            
            
            no_of_points = size(lines{i}(:,1));
            no_of_points = no_of_points(1);
  
            

            if no_of_points>minimum_points_for_spiral
                spiral_length = ceil(density_window*no_of_points);
                % SPIRAL ASSUMED ONLY AT ENDS
                endpoints = lines{i}(end-spiral_length:end,:);
                startpoints = lines{i}(1:spiral_length,:);
                % is it a spiral?
                endpoints_radius = norm(endpoints-endpoints(end,:));
                startpoints_radius = norm(startpoints-startpoints(1,:));
                % - since density is proportional to the radius squared, we
                % can just divide the number of points by the radius
                % squared to get a comparable number
                endpoints_density = spiral_length/(endpoints_radius^2);
                startpoints_density = spiral_length/(startpoints_radius^2);

                if endpoints_density>density_threshold
%                     disp(i)
                    % truncate spiral by  10%
                    endpoints = lines{i}(end-ceil(truncation_percentage*no_of_points):end,:);
                    endpoints_radius = norm(endpoints-endpoints(end,:));
                    while endpoints_radius<5.1
                        lines{i}=lines{i}(1:end-ceil(truncation_percentage*no_of_points),:);
                        endpoints = lines{i}(end-ceil(truncation_percentage*no_of_points):end,:);
                        endpoints_radius = norm(endpoints-endpoints(end,:));
                    
                    end
                    
                end
                if startpoints_density>density_threshold
%                     disp(i)
                    % truncate spiral by  10%
                    startpoints = lines{i}(1:ceil(truncation_percentage*no_of_points),:);
                    startpoints_radius = norm(startpoints-startpoints(1,:));
                    while startpoints_radius<5.1
                        lines{i}=lines{i}(ceil(truncation_percentage*no_of_points):end,:);
                        startpoints = lines{i}(1:ceil(truncation_percentage*no_of_points),:);
                        startpoints_radius = norm(startpoints-startpoints(1,:));
                    end
                end
                
            end
 end

 function [lines] = correctSpiralOlder(lines,i)
    % ++++++++++   OLDER    ++++++++++++
    if i==157
        [vert,D] = correctSpiral(flip(lines{i}),PrtOpt.bandwidth); 
        [vert2,ia,ib] = intersect(lines{i},vert, 'rows','stable'); %intersect(A,B) returns the data common to both A and B, with no repetitions. verts=C is in sorted order. Generally, C = A(ia) and C = B(ib).
        D_comm = d_average(ia); 
%             lines{i} = vert; 
        d_average = min([D_comm,D],[],2); %find the smallest distance between the line to itself (D) and the line to others (D_comm)
        
    end

    if i==159 %here the spiral is first, we need to flip
        disp(lines{i});
        [vert,D] = correctSpiral(lines{i},PrtOpt.bandwidth); 
%             vert = flip(vert); D = flip(D); 
        [vert2,ia,ib] = intersect(lines{i},vert, 'rows','stable'); %intersect(A,B) returns the data common to both A and B, with no repetitions. verts=C is in sorted order. Generally, C = A(ia) and C = B(ib).
        D_comm = d_average(ia); 
%             lines{i} = vert; 
        d_average = min([D_comm,D],[],2); %find the smallest distance between the line to itself (D) and the line to others (D_comm)
        
    end
 end
