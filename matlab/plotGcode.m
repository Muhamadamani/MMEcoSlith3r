 function [] = plotGcode(layer)
    hold on
    for iLayer = 1:length(layer)
        figure; 
        tit = sprintf('G-code waypoints, Layer %d', iLayer);
        title(tit);
        for i = 1:length(layer(iLayer).Course)
            pts = layer(iLayer).Course(i).POINT;
            if isempty(pts)
                continue
            end
            dist = pts(:,4); 
            x = pts(:,1); y = pts(:,2);
        %     scatter(x,y,20*dist,dist,'filled');
            x(end+1) = NaN;
            y(end+1) = NaN;
            dist = circshift(dist,-1); 
            dist(end+1) = NaN; 
        

            patch(x,y,dist,'EdgeColor','Flat', 'Marker','.','MarkerFaceColor','flat','LineWidth',3,'MarkerSize',15); %what we hope to print;
        end
         set(gca,'XColor', 'none','YColor','none','Fontsize', 16)
        set(gca,'color','none')
        colorbar()
         colormap(brewermap([],"-YlGnBu"))
         axis equal

    end
end
