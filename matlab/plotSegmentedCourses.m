function plotSegmentedCourses(segmented)
% Visualize segmented courses: bamboo=green, carbon=black

  colors = struct('bamboo',[0,0.6,0],'carbon',[0,0,0]);
  figure; hold on; axis equal;
  title('Segmented Courses by Material');
  legendEntries = {};

  for L = 1:numel(segmented)
    for c = 1:numel(segmented(L).Course)
      S = segmented(L).Course(c);
      col = colors.(char(S.material));
      plot(S.POINT(:,1), S.POINT(:,2), 'Color',col,'LineWidth',1.2);
      legendEntries{end+1} = char(S.material); %#ok<AGROW>
    end
  end

  % unique legend
  [uniq,ia] = unique(legendEntries,'stable');
  legend(uniq);
end
