function PlotQuiver(pltOpt,ANGLES)
    if strcmp(pltOpt.plot_quiver, 'yes')
     nLayer = length(ANGLES); 
     for i = 1:nLayer
        figure()
        U = ANGLES(i).U; V = ANGLES(i).V; 
        X = ANGLES(i).X; Y = ANGLES(i).Y; 

        Un = U./sqrt(U.^2 + V.^2);
        Vn = V./sqrt(U.^2 + V.^2);

        quiver(X, Y, Un, Vn, 'Color', 'k', 'LineWidth',1, 'AutoScale','off') ;

        axis equal 
        axis padded
        set(gca,'XColor', 'none','YColor','none', 'FontSize',14,'FontName', 'Myriad Pro')
        title(strcat('Angle Distribution - Layer ', string(i)));

        if strcmpi(pltOpt.save_plots,'yes')
            figname = strcat(pltOpt.foldername,'Quiver_', string(i));
            savefig(figname); 
            saveas(gcf,figname,'png')
        end      

    end
    end
end