function GCodeFormatNew(layerReorder, prtOpt, segmented)
% Emit multi-material G-code using the segmented runs

  fid = fopen(prtOpt.gcode_fname,'w')
 % gcode_fname_2 = gcode_fname + "_2_temp"
%  fid_2 = fopen(prtOpt.gcode_fname_2,'w');

  if fid==-1, error('Cannot open %s',prtOpt.gcode_fname); end
 % if fid_2==-1, error('Cannot open %s',prtOpt.gcode_fname_2); end

  % Tool definitions
 % tools.bamboo.T    = 'T0';
 tools.bamboo.T = fileread(strcat(prtOpt.gcodeExtremes_foldername, 'T2_to_T1_tool_change.gcode'));

  tools.bamboo.TEMP = prtOpt.temp_bamboo;
  %tools.carbon.T    = 'T1';
  tools.carbon.T = fileread(strcat(prtOpt.gcodeExtremes_foldername, 'T1_to_T2_tool_change.gcode'));

  tools.carbon.TEMP = prtOpt.temp_carbon;
  lastTool = "";

  totE = 0; totT = 0;
  nL = numel(segmented);
  %% mat_0 = "";

  for L = 1:nL
    fprintf(fid,'\n;--- LAYER %d ---',L);
    for s = 1:numel(segmented(L).Course)
      seg = segmented(L).Course(s);
      P   = seg.POINT;
      mat = char(seg.material);
      tool = tools.(mat);
        % if isempty(mat_0)
        %     mat_0 = tool;
        % end


% % % % %      Tool change if needed
% % % %       if ~strcmp(lastTool,mat)
% % % %         if ~isempty(lastTool)
% % % %           fprintf(fid,'\nG92 E0\nG1 E-2 F2400 ; retract');
% % % %         end
% % % %         fprintf(fid,'\n%s ; switch to %s',tool.T,mat);
% % % %         fprintf(fid,'\nM104 S%d ; set temp',tool.TEMP);
% % % %         fprintf(fid,'\nG1 X0 Y0 F3000 ; purge loc\nG1 E5 F300 ; purge');
% % % %         lastTool = mat;
% % % %       end
        
%        if strcmp(mat_0,mat)
        
      z = prtOpt.layer_height * L;
      fprintf(fid,'\n; SEGMENT %d (%s)',s,mat);
      fprintf(fid,'\nG1 X%.4f Y%.4f Z%.4f',P(1,1),P(1,2),z);
      curr = [P(1,1),P(1,2),z];

      for i = 2:size(P,1)
        nxt  = [P(i,1),P(i,2),z];
        dist = norm(nxt - curr);
        ext  = 4*(dist * prtOpt.layer_height * P(i,4))/(pi*prtOpt.fil_dia^2);
        fprintf(fid,'\nG1 X%.4f Y%.4f Z%.4f E%.4f F%d', ...
                nxt(1),nxt(2),nxt(3),ext,prtOpt.print_speed);
        totE = totE + ext;
        totT = totT + dist/prtOpt.print_speed;
        curr = nxt;
      end

        % else %%%%

% z = prtOpt.layer_height * L;
%       fprintf(fid_2,'\n; SEGMENT %d (%s)',s,mat);
%       fprintf(fid_2,'\nG1 X%.4f Y%.4f Z%.4f',P(1,1),P(1,2),z);
%       curr = [P(1,1),P(1,2),z];
% 
%       for i = 2:size(P,1)
%         nxt  = [P(i,1),P(i,2),z];
%         dist = norm(nxt - curr);
%         ext  = 4*(dist * prtOpt.layer_height * P(i,4))/(pi*prtOpt.fil_dia^2);
%         fprintf(fid_2,'\nG1 X%.4f Y%.4f Z%.4f E%.4f F%d', ...
%                 nxt(1),nxt(2),nxt(3),ext,prtOpt.print_speed);
%         totE = totE + ext;
%         totT = totT + dist/prtOpt.print_speed;
%         curr = nxt;
%       end


        % end %%%%%



    end
  end

  fclose(fid);
 % fclose(fid_2);

  % Prepend/append begin+end text
  header  = sprintf(';FLAVOR: MARLIN\n;Total filament (m): %.2f\n;Est time (min): %.1f\n', ...
                    totE/1000, totT);
  beginTxt = fileread(fullfile(prtOpt.gcodeExtremes_foldername,'begin_text.gcode'));
  core     = fileread(prtOpt.gcode_fname);
 % core_2     = fileread(prtOpt.gcode_fname_2);
  endTxt   = fileread(fullfile(prtOpt.gcodeExtremes_foldername,'end_text.gcode'));
%  allG    = strjoin({header,beginTxt,core,core_2,endTxt},'\n');
  allG    = strjoin({header,beginTxt,core,endTxt},'\n');

  fid = fopen(prtOpt.gcode_fname,'w');
  fwrite(fid, allG, 'char');
  fclose(fid);
end
