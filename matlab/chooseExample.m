function [ANGLES,dim,prtOpt,pltOpt] = chooseExample(boolExample)
%chooseExample This function prompts the user to choose between available
%example codes in Slith3r issued from the paper, if boolExample == 1

    if boolExample
%         opts.Default = 'Wood';
%         answer = questdlg('Please choose example', ...
% 	        'Slith3r', ...
% 	        'Wood','Starry Night','Figure 1','Chair','Payload Adaptor',opts);
%     
%         % Handle response
%         switch answer
%             case 'Wood'
%                 exampleType = 1;
%             case 'Starry Night'
%                 exampleType = 1;
%             case 'Figure 1'
%                 exampleType = 3;
%             case 'Chair'
%                 exampleType = 1;
%             case 'Payload adaptor'
%                 exampleType = 3;
%         end
        cd examples
        d = dir('**/*.mat');
        fn = {d.name};
        [indx,tf] = listdlg('PromptString',{'Select a file.',...
            'Only one file can be selected at a time.',''},...
            'SelectionMode','single','ListString',fn);

        if tf
            file = load(fn{indx}); 
            ANGLES = file.ANGLES;
            dim = file.dim;
            prtOpt = file.prtOpt; 
            pltOpt = file.pltOpt; 
        else
            display('No example has been selected, please load something else manually')
        end
        cd ..
    else
        display('Please load something else manually')
    end
end