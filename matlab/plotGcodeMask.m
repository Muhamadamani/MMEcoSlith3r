function [] = plotGcodeMask(layer, prtOpt)
    % PLOTGCODE  Show courses overlaid on true FE boundary loops
    %
    %   plotGcode(layer, prtOpt)
    %
    %   layer is your Course struct array (after masking / reordering)
    %   prtOpt is only used to locate mesh_data_loops.mat

    %% 1) load boundary loops
    baseFolder = '/Users/mamani/Downloads/slith3r_mu_main/examples/multimaterial_matlab_output/';
    M = load(fullfile(baseFolder,'mesh_data_loops.mat'),'perim_loops');
    loops = M.perim_loops;  % cell array of N×2 arrays

    %% 2) compute overall bounds from loops
    allLoopPts = vertcat(loops{:});
    xmin = min(allLoopPts(:,1));  xmax = max(allLoopPts(:,1));
    ymin = min(allLoopPts(:,2));  ymax = max(allLoopPts(:,2));

    %% 3) plot
    figure; hold on;
    title('All Courses Overlaid on True Boundary');
    
    % draw each loop
    for k = 1:numel(loops)
        pts = loops{k};
        plot(pts(:,1), pts(:,2), 'k-', 'LineWidth', 1.5);
    end

    % draw courses
    for L = 1:numel(layer)
      for C = 1:numel(layer(L).Course)
        pts = layer(L).Course(C).POINT;
        if isempty(pts), continue; end
        x = pts(:,1); y = pts(:,2);
        % you can color by width or just use a flat color
        plot(x, y, 'b-', 'LineWidth', 1);
      end
    end

    % enforce full view
    axis equal;
    xlim([xmin xmax]);
    ylim([ymin ymax]);
    xlabel('X (mm)');
    ylabel('Y (mm)');
    set(gca,'FontSize',14);
    box on;
    hold off;
end
