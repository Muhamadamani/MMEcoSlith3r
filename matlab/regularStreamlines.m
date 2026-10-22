function LAYER = regularStreamlines(ANGLES, prtOpt, integStep, Nmem,pltOpt)
    % this seeds streamlines with a target line width in mind, suited for
    % parallel lines. The first seeding points are spaced along the
    % specified edge, spaced by targetwidth. This is to ensure control of
    % spacing for zones that are simple enough and should be regular. 
    % prtOpt.Edge = [x1 y1; x2 y2] ; ideally this edge is perpendicular to most
    % future streamlines 
    % prtOpt.targetwidth - float representing ideal spacing between streamlines
    

    bandwidth = prtOpt.upperbound;
    targetwidth = prtOpt.targetwidth; 
    trimdist = prtOpt.lowerbound; %determines lower bounds of line width 

    Edge = prtOpt.Edge; 
    lines = cell(1); %keep vertices in memory 
    linenum = 1; %line counter

    nLayer = length(ANGLES);
    distEdge =  sqrt(sum(diff(prtOpt.Edge).^2));
    nSeed = floor(distEdge/targetwidth); 
    init_seedpoints = [linspace(Edge(1,1),Edge(2,1),nSeed);linspace(Edge(1,2),Edge(2,2),nSeed)]'; 
    
    for lnum = 1:nLayer
        figure;
        U = ANGLES(lnum).U; V = ANGLES(lnum).V; 
        X = ANGLES(lnum).X; Y = ANGLES(lnum).Y; 
        set(0,'DefaultFigureVisible','on');
    
        minx = min(X,[],"all");          miny = min(Y,[],"all");       
        Lx = max(X,[],"all") - minx;     Ly = max(Y,[],"all") - miny;
        
        %assign edges of the domain as seeding points for the Delaunay
        %triangulation
        verts = initFrame(ANGLES,lnum,bandwidth); 
 
        QUEUE = init_seedpoints; 
        verts = []; 
        linenum = 1; 


        while ~isempty(QUEUE)
            startx = QUEUE(end,1); 
            starty = QUEUE(end,2);  
            [hf,ic] = mmstream2(X, Y, U, V, startx, starty,'o', integStep,Nmem);
            if size(hf{1}(:,1)) <=3 %too short, probably the line should be in the other direction 
                %the function returns only one point because the seedpoint is on the
                %edge and the streamline directs outside the edge.
                [hf,ic] = mmstream2(X, Y, -U, -V, startx, starty,'s', integStep,Nmem);
            end

%              vvf = trim_streamline(verts, vvf, trimdist);
%             size(hf{1}(:,1))
            vv = [hf{1}(:,1) hf{1}(:,2)]; 
            vv = trim_streamline(verts, vv, trimdist);
%             if ~isempty(hf)
%                 vvf = [hf{1}(:,1) hf{1}(:,2)]; 
%                 vvf = trim_streamline(verts(idXframe:end,:), ...
%                     vvf, trimdist);
%             else disp('Problem at hf')
%             end


                hold on
                if strcmp(pltOpt.plot_createStreamlines, 'yes')
                    set(0,'DefaultFigureVisible','on')
                    plot(vv(:,1), vv(:,2), 'b-', 'Linewidth', 0.7, 'Color', 'k')
                    set(gca,'XColor', 'none','YColor','none')
                    axis equal
                end
               
                % add new-found streamline to the list
                vv = unique(vv,'stable','rows'); 
                lines{linenum} = vv;
                linenum = linenum + 1;
                
                %update Delaunay triangulation to find new seeding candidates
                verts = [verts; vv ];
     
            QUEUE(end,:) = []; 
        end
%        
        verts = [verts; initFrame(ANGLES,lnum,bandwidth)]; 
       td = delaunayTriangulation(verts);

        
        % Detects all possible seeding points (circumcenters) inside domain,
        [C, r] = circumcenter(td);
        mask = C(:,1) >= minx & C(:,1) <= minx+Lx &...
                C(:,2) > miny & C(:,2) <= miny+Ly;
    
        C = C(mask,:);
        r = r(mask,:);
    
        % find largest r
        id = find(r == max(r),1);
        
        %first seeding point 
        startx = round(C(id,1),4);
        starty = round(C(id,2),4);
    
        while max(r) >= bandwidth/2
            fh(nLayer + 3*lnum-2) = figure(nLayer + 3*lnum-2);       
            title("Streamline Generation, Layer " + " " + num2str(lnum)); 
            axis equal

            hold on; 

            [hf,ic] = mmstream2(X, Y, U, V, startx, starty,'s', integStep,Nmem);

            if ~isempty(hf)
                vvf = [hf{1}(:,1) hf{1}(:,2)]; 
                vvf = trim_streamline(verts(1:end,:), ...
                    vvf, trimdist);
            else disp('Problem at hf')
            end

            if ic == false %no need to go backward if the previous was closed
            %backward streamline 
                [hb,ic] = mmstream2(X, Y, -U, -V, startx, starty, 's', integStep,Nmem);
                 if ~isempty(hb)
    %                 hb.Visible = 'off';
    %                 vvb = [hb.XData' hb.YData'];
                    vvb = [hb{1}(:,1) hb{1}(:,2)]; 
                    vvb = trim_streamline(verts(1:end,:), ...
                        vvb, trimdist);
                else disp('Problem at hb')
                 end
              %concatenate to form full line with whatever exists
                if isempty(hf)&&(~isempty(hb)) 
                    vv = [flipud(vvb)]; 
                elseif isempty(hb)&&(~isempty(hf))
                    vv =  vvf(2:end,:);
                else
                    vv = [flipud(vvb);...
                          vvf(2:end,:)];
                end
            else %streamline is closed
                vv = vvf; 
            end

            hold on
            if strcmp(pltOpt.plot_createStreamlines, 'yes')
                set(0,'DefaultFigureVisible','on')
                plot(vv(:,1), vv(:,2), 'b-', 'Linewidth', 0.7, 'Color', 'k')
                set(gca,'XColor', 'none','YColor','none')
            end
           
            % add new-found streamline to the list
            vv = unique(vv,'stable','rows'); 
            lines{linenum} = vv;
            linenum = linenum + 1;
            
            %update Delaunay triangulation to find new seeding candidates
            verts = [verts; vv ];
 
            td = delaunayTriangulation(verts);

            [C, r] = circumcenter(td);
%             mask = C(:,1) >= minx & C(:,1) <= minx+Lx &...
%                     C(:,2) > miny & C(:,2) <= miny+Ly &...
%                     r >= bandwidth/2/satratio;
            bw = bandwidth/3; %if the radius is too close to the edge, the radius will be bigger than the actual space between the 2 SL and the next streamline won't be centered
            mask = C(:,1) >= minx+bw & C(:,1) <= minx+Lx-bw &...
                    C(:,2) > miny+bw & C(:,2) <= miny+Ly-bw &...
                    r >= bandwidth/2;


            C = C(mask,:);
            r = r(mask,:);

            % find largest r
            id = find(r == max(r),1);


            %new seeding point 
            startx = round(C(id,1),4);
            starty = round(C(id,2),4);
%             % draw a circle 

            if strcmpi(pltOpt.plot_Triangles,'yes')
                figure(nLayer + 3*lnum-1);
                hold on
                axis image
                tp = triplot(td, 'Linewidth', 0.2, 'Color','#4DBEEE');
                xlim([minx-0.01, minx+Lx+0.01])
                ylim([miny-0.01, miny+Ly+0.01])
                kk = scatter(C(id,1), C(id,2), 100, 'Marker', 'o', 'MarkerEdgeColor', 'k', 'MarkerFaceColor', 'k');
                hold on
                plot_circ(startx, starty, max(r), nLayer + 3*lnum-1)
            end
        end %end of while loop: can't fit any circle anymore
    
    
            if strcmpi(pltOpt.plot_createStreamlines,'yes')&&strcmpi(pltOpt.save_plots,'yes')
    %             set(0,'DefaultFigureVisible','on');
                set(gca, 'FontName', 'Myriad Pro')
                set(gca,'XColor', 'none','YColor','none')
                figname = strcat(pltOpt.foldername,'Streamlines_', string(lnum));
                savefig(figname); 
                saveas(gcf,figname,'png')
            end
    
    %%%%%%%% get distance of each line from neighbors %%%%%%%%%
            figure(nLayer + 3*lnum);
            colormap(brewermap([],"-YlGnBu"))
            axis equal
            hold on
            set(gca, 'FontName', 'Arial')
            set(gca,'XColor', 'none','YColor','none','Fontsize', 12)
            for i = 1:length(lines)
                [d_average, lines] = GetDistance(lines,i,prtOpt); 
    
                if strcmpi(pltOpt.plot_Distance, 'yes')

                    ps = plot([minx-0.01, minx+Lx+0.01],[miny-0.01, miny+Ly+0.01], 'b.');
                    sz  = 10*d_average; 

                    scatter(lines{i}(:,1), lines{i}(:,2), sz', d_average',"filled");
                    ps.Visible = 'off';
                    set(gca,'XColor', 'none','YColor','none')
                    title("Distance calculation, Layer" + " " + num2str(lnum)); 
                    drawnow
    
    
                end
                padding = zeros(size(lines{i}(:,1)));
                % save vertices with distance into structure 
                LAYER(lnum).Course(i) = struct('POINT', [lines{i}, padding, d_average]);
            end
    
            if strcmpi(pltOpt.plot_Distance, 'yes') %add graphical features at the end to win time 
                    figure(nLayer + 3*lnum);
%                     title("Line widths, Layer" + " " + num2str(lnum)); 

                    colorbar()
                    if strcmpi(pltOpt.save_plots, 'yes')
                        set(gca,'color','none')
                        figname = strcat(pltOpt.foldername,'Distance_', string(lnum));                     
                        savefig(figname); 
                        saveas(gcf,figname,'png')
                    end
            end
    end
end