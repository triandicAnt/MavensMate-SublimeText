# Written by Joe Ferraro (@joeferraro / www.joe-ferraro.com)
import os
import subprocess 
import json
import sys

#dist_dir = os.path.dirname(os.path.abspath(__file__))
#sys.path.insert(0, dist_dir)

try:
    # Python 3
    import MavensMate.config as config
    import MavensMate.util as util
    from MavensMate.lib import command_helper
    import MavensMate.lib.mm_interface as mm
    #from lib.printer import PanelPrinter
    from MavensMate.lib.printer import PanelPrinter
except ValueError as e:
    print(">>>>>> ", e.message)
    # Python 2
    import util 
    import config
    from lib.printer import PanelPrinter
    from lib.threads import ThreadTracker
    import command_helper 

import sublime
import sublime_plugin

settings = sublime.load_settings('mavensmate.sublime-settings')
sublime_version = int(float(sublime.version()))

st_version = 2
# Warn about out-dated versions of ST3
if sublime.version() == '':
    st_version = 3
elif int(sublime.version()) > 3000:
    st_version = 3

if st_version == 3:
    installed_dir, _ = __name__.split('.')
elif st_version == 2:
    installed_dir = os.path.basename(os.getcwd())

reloader_name = 'lib.reloader'

# ST3 loads each package as a module, so it needs an extra prefix
if st_version == 3:
    reloader_name = 'MavensMate.' + reloader_name
    from imp import reload

# Make sure all dependencies are reloaded on upgrade
if reloader_name in sys.modules:
    reload(sys.modules[reloader_name])

try:
    # Python 3
    from .lib import reloader
except (ValueError):
    # Python 2
    from lib import reloader


####### <--START--> COMMANDS THAT USE THE MAVENSMATE UI ##########

#displays new project dialog
class NewProjectCommand(sublime_plugin.ApplicationCommand):
    def run(command):
        util.check_for_workspace()
        mm.call('new_project', False)
        util.send_usage_statistics('New Project')

#displays edit project dialog
class EditProjectCommand(sublime_plugin.ApplicationCommand):
    def run(command):
        mm.call('edit_project', False)
        util.send_usage_statistics('Edit Project')

    def is_enabled(command):
        return util.is_mm_project()

#displays unit test dialog
class RunApexUnitTestsCommand(sublime_plugin.ApplicationCommand):
    def run(command):
        active_file = util.get_active_file()
        try:
            if os.path.exists(active_file):
                filename, ext = os.path.splitext(os.path.basename(util.get_active_file()))
                if ext == '.cls':
                    params = {
                        "selected"         : [filename]
                    }
                else:
                    params = {}
            else:
                params = {}
        except:
            params = {}
        mm.call('unit_test', context=command, params=params)
        util.send_usage_statistics('Apex Unit Testing')

    def is_enabled(command):
        return util.is_mm_project()

#launches the execute anonymous UI
class ExecuteAnonymousCommand(sublime_plugin.ApplicationCommand):
    def run(command):
        mm.call('execute_apex', False)
        util.send_usage_statistics('Execute Anonymous')

    def is_enabled(command):
        return util.is_mm_project()

#displays deploy dialog
class DeployToServerCommand(sublime_plugin.ApplicationCommand):
    def run(command):
        mm.call('deploy', False)
        util.send_usage_statistics('Deploy to Server')

    def is_enabled(command):
        return util.is_mm_project()

####### <--END--> COMMANDS THAT USE THE MAVENSMATE UI ##########

class MavensStubCommand(sublime_plugin.WindowCommand):
    def run(self):
        return True
    def is_enabled(self):
        return False
    def is_visible(self):
        return not util.is_mm_project();

#deploys the currently active file
class CompileActiveFileCommand(sublime_plugin.WindowCommand):
    def run(self):       
        params = {
            "files" : [util.get_active_file()]
        }
        mm.call('compile', context=self, params=params)

    def is_enabled(command):
        return util.is_mm_file()

    def is_visible(command):
        return util.is_mm_project()

#handles compiling to server on save
class RemoteEdit(sublime_plugin.EventListener):
    def on_post_save(self, view):
        settings = sublime.load_settings('mavensmate.sublime-settings')
        if settings.get('mm_compile_on_save') == True and util.is_mm_file() == True:
            params = {
                "files" : [util.get_active_file()]
            }
            mm.call('compile', context=view, params=params)

class MenuModifier(sublime_plugin.EventListener):
    def on_activated_async(self, view):
        view.file_name()

#compiles the selected files
class CompileSelectedFilesCommand(sublime_plugin.WindowCommand):
    def run (self, files):
        #print files
        params = {
            "files"         : files
        }
        mm.call('compile', context=self, params=params)
        util.send_usage_statistics('Compile Selected Files')

    def is_visible(self, files):
        return util.is_mm_project()

    def is_enabled(self, files):
        if files != None and type(files) is list and len(files) > 0:
            for f in files:
                if util.util.is_mm_file(f):
                    return True
        return False

#deploys the currently open tabs
class CompileTabsCommand(sublime_plugin.WindowCommand):
    def run (self):
        params = {
            "files"         : util.get_tab_file_names()
        }
        mm.call('compile', context=self, params=params)
        util.send_usage_statistics('Compile Tabs')

#replaces local copy of metadata with latest server copies
class CleanProjectCommand(sublime_plugin.WindowCommand):
    def run(self):
        if sublime.ok_cancel_dialog("Are you sure you want to clean this project? All local (non-server) files will be deleted and your project will be refreshed from the server", "Clean"):
            mm.call('clean_project', context=self)
            util.send_usage_statistics('Clean Project')

    def is_enabled(command):
        return util.is_mm_project()  

#opens a project in the current workspace
class OpenProjectCommand(sublime_plugin.WindowCommand):
    def run(self):
        util.check_for_workspace()
        open_projects = []
        try:
            for w in sublime.windows():
                if len(w.folders()) == 0:
                    continue;
                root = w.folders()[0]
                if util.mm_workspace() not in root:
                    continue
                project_name = root.split("/")[-1]
                open_projects.append(project_name)
        except:
            pass

        import os
        self.dir_map = {}
        dirs = [] 
        print(util.mm_workspace())
        for dirname in os.listdir(util.mm_workspace()):
            if dirname == '.DS_Store' or dirname == '.' or dirname == '..' or dirname == '.logs' : continue
            if dirname in open_projects : continue
            if not os.path.isdir(util.mm_workspace()+"/"+dirname) : continue
            sublime_project_file = dirname+'.sublime-project'
            for project_content in os.listdir(util.mm_workspace()+"/"+dirname):
                if '.' not in project_content: continue
                if project_content == '.sublime-project':
                    sublime_project_file = '.sublime-project'
                    continue
            dirs.append(dirname)
            self.dir_map[dirname] = [dirname, sublime_project_file]
        self.results = dirs
        print(self.results)
        self.window.show_quick_panel(dirs, self.panel_done,
            sublime.MONOSPACE_FONT)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        self.picked_project = self.results[picked]
        print('opening project: ' + self.picked_project)
        project_file = self.dir_map[self.picked_project][1]
        if os.path.isfile(util.mm_workspace()+"/"+self.picked_project+"/"+project_file):
            if sublime_version >= 3000:
                p = subprocess.Popen("'/Applications/Sublime Text 3.app/Contents/SharedSupport/bin/subl' --project '"+util.mm_workspace()+"/"+self.picked_project+"/"+project_file+"'", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            else:
                p = subprocess.Popen("'/Applications/Sublime Text 2.app/Contents/SharedSupport/bin/subl' --project '"+util.mm_workspace()+"/"+self.picked_project+"/"+project_file+"'", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        else:
            sublime.message_dialog("Cannot find: "+util.mm_workspace()+"/"+self.picked_project+"/"+project_file)

#displays new apex class dialog
class NewApexClassCommand(sublime_plugin.TextCommand):
    def run(self, edit, api_name="MyClass", class_type="default"): 
        templates = get_merged_apex_templates("ApexClass")
        sublime.active_window().show_input_panel("Apex Class Name, Template "+str(sorted(templates.keys())), api_name+", "+class_type, self.on_input, None, None)
        util.send_usage_statistics('New Apex Class')

    def on_input(self, input): 
        api_name, class_type = [x.strip() for x in input.split(',')]
        if not check_apex_templates(get_merged_apex_templates("ApexClass"), { "api_name":api_name, "class_type":class_type }, "new_apex_class"):
            return
        options = {
            'metadata_type'     : 'ApexClass',
            'metadata_name'     : api_name,
            'apex_class_type'   : class_type
        }
        mm.call('new_metadata', params=options) 

    def is_enabled(self):
        return util.is_mm_project()

#displays new apex trigger dialog
class NewApexTriggerCommand(sublime_plugin.TextCommand):
    def run(self, edit, api_name="MyAccountTrigger", sobject_name="Account", class_type="default"): 
        templates = get_merged_apex_templates("ApexTrigger")
        sublime.active_window().show_input_panel("Apex Trigger Name, SObject Name, Template "+str(sorted(templates.keys())), api_name+", "+sobject_name+", "+class_type, self.on_input, None, None)
        util.send_usage_statistics('New Apex Trigger')

    def on_input(self, input):
        api_name, sobject_name, class_type = [x.strip() for x in input.split(',')]
        if not check_apex_templates(get_merged_apex_templates("ApexTrigger"), { "api_name":api_name, "sobject_name":sobject_name, "class_type":class_type }, "new_apex_trigger"):
            return
        options = {
            'metadata_type'     : 'ApexTrigger',
            'metadata_name'     : api_name,
            'object_api_name'   : sobject_name,
            'apex_class_type'   : class_type
        }
        mm.call('new_metadata', params=options) 

    def is_enabled(command):
        return util.is_mm_project() 

#displays new apex page dialog
class NewApexPageCommand(sublime_plugin.TextCommand):
    def run(self, edit, api_name="MyPage", class_type="default"): 
        templates = get_merged_apex_templates("ApexPage")
        sublime.active_window().show_input_panel("Visualforce Page Name, Template", api_name+", "+class_type, self.on_input, None, None)
        util.send_usage_statistics('New Visualforce Page')
    
    def on_input(self, input): 
        api_name, class_type = [x.strip() for x in input.split(',')]
        if not check_apex_templates(get_merged_apex_templates("ApexPage"), { "api_name":api_name, "class_type":class_type }, "new_apex_page"):
            return
        options = {
            'metadata_type'     : 'ApexPage',
            'metadata_name'     : api_name,
            'apex_class_type'   : class_type
        }
        mm.call('new_metadata', params=options) 

    def is_enabled(command):
        return util.is_mm_project()

#displays new apex component dialog
class NewApexComponentCommand(sublime_plugin.TextCommand):
    def run(self, edit, api_name="MyComponent", class_type="default"): 
        templates = get_merged_apex_templates("ApexComponent")
        sublime.active_window().show_input_panel("Visualforce Component Name, Template", api_name+", "+class_type, self.on_input, None, None)
        util.send_usage_statistics('New Visualforce Component')
    
    def on_input(self, input): 
        api_name, class_type = [x.strip() for x in input.split(',')]
        if not check_apex_templates(get_merged_apex_templates("ApexComponent"), { "api_name":api_name, "class_type":class_type }, "new_apex_component"):
            return
        options = {
            'metadata_type'     : 'ApexComponent',
            'metadata_name'     : api_name,
            'apex_class_type'   : class_type
        }
        mm.call('new_metadata', params=options) 

    def is_enabled(command):
        return util.is_mm_project()

def check_apex_templates(templates, args, command):
    if "class_type" not in args or args["class_type"] not in templates:
        sublime.error_message(str(args["class_type"])+" is not a valid template, please choose one of: "+str(sorted(templates.keys())))
        sublime.active_window().run_command(command, args)
        return False
    return True

def get_merged_apex_templates(apex_type):
    settings = sublime.load_settings('mavensmate.sublime-settings')
    template_map = settings.get('mm_default_apex_templates_map', {})
    custom_templates = settings.get('mm_apex_templates_map', {})
    if apex_type not in template_map:
        return {}
    if apex_type in custom_templates:
        template_map[apex_type] = dict(template_map[apex_type], **custom_templates[apex_type])
    return template_map[apex_type]

#displays mavensmate panel
class ShowDebugPanelCommand(sublime_plugin.WindowCommand):
    def run(self): 
        if util.is_mm_project() == True:
            PanelPrinter.get(self.window.id()).show(True)

#hides mavensmate panel
class HideDebugPanelCommand(sublime_plugin.WindowCommand):
    def run(self):
        if util.is_mm_project() == True:
            PanelPrinter.get(self.window.id()).show(False)

#shows mavensmate info modal
class ShowVersionCommand(sublime_plugin.ApplicationCommand):
    def run(command):
        version = util.get_version_number()
        sublime.message_dialog("MavensMate for Sublime Text v"+version+"\n\nMavensMate for Sublime Text is an open source Sublime Text package for Force.com development.\n\nhttp://mavens.io/mm")

#refreshes selected directory (or directories)
# if src is refreshed, project is "cleaned"
class RefreshFromServerCommand(sublime_plugin.WindowCommand):
    def run (self, dirs, files):
        if sublime.ok_cancel_dialog("Are you sure you want to overwrite the selected files' contents from Salesforce?", "Refresh"):
            if dirs != None and type(dirs) is list and len(dirs) > 0:
                params = {
                    "directories"   : dirs
                }
            elif files != None and type(files) is list and len(files) > 0:
                params = {
                    "files"         : files
                }
            mm.call('refresh', context=self, params=params)
            util.send_usage_statistics('Refresh Selected From Server')

    def is_visible(self, dirs, files):
        return util.is_mm_project()

    def is_enabled(self, dirs, files):
        if dirs != None and type(dirs) is list and len(dirs) > 0:
            for d in dirs:
                if util.is_config.mm_dir(d):
                    return True
        if files != None and type(files) is list and len(files) > 0:
            for f in files:
                if util.util.is_mm_file(f):
                    return True
        return False

class RefreshActivePropertiesFromServerCommand(sublime_plugin.WindowCommand):
    def run (self):
        if sublime.ok_cancel_dialog("Are you sure you want to overwrite the selected files' apex properties from Salesforce?", "Refresh Apex Properties"):
            params = {
                "files"         : [util.get_active_file()]
            }
            mm.call('refresh_properties', context=self, params=params)
            util.send_usage_statistics('Refresh Active Properties From Server')

    def is_visible(self):
        if not util.is_mm_file():
            return False
        filename = util.get_active_file()
        basename = os.path.basename(filename)
        data = util.get_apex_file_properties()
        if not basename in data:
            return True
        elif 'conflict' in data[basename] and data[basename]['conflict'] == True:
            return True
        else:
            return False

class RefreshPropertiesFromServerCommand(sublime_plugin.WindowCommand):
    def run (self, dirs, files):
        if sublime.ok_cancel_dialog("Are you sure you want to overwrite the selected files' apex properties from Salesforce?", "Refresh Apex Properties"):
            if dirs != None and type(dirs) is list and len(dirs) > 0:
                params = {
                    "directories"   : dirs
                }
            elif files != None and type(files) is list and len(files) > 0:
                params = {
                    "files"         : files
                }
            mm.call('refresh_properties', context=self, params=params)
            util.send_usage_statistics('Refresh Selected Properties From Server')

    def is_visible(self, dirs, files):
        if not util.is_mm_project():
            return False
        if files != None and type(files) is list and len(files) > 0:
            filename = files[0]
            basename = os.path.basename(filename)
            data = util.get_apex_file_properties()
            if not basename in data:
                return True
            elif 'conflict' in data[basename] and data[basename]['conflict'] == True:
                return True
            else:
                return False
        return True

    def is_enabled(self, dirs, files):
        if dirs != None and type(dirs) is list and len(dirs) > 0:
            for d in dirs:
                if util.is_config.mm_dir(d):
                    return True
        if files != None and type(files) is list and len(files) > 0:
            for f in files:
                if util.util.is_mm_file(f):
                    return True
        return False

#refreshes the currently active file from the server
class RefreshActiveFileCommand(sublime_plugin.WindowCommand):
    def run(self):
        if sublime.ok_cancel_dialog("Are you sure you want to overwrite this file's contents from Salesforce?", "Refresh"):
            params = {
                "files"         : [util.get_active_file()]
            }
            mm.call('refresh', context=self, params=params)
            util.send_usage_statistics('Refresh Active File From Server')

    def is_visible(self):
        return util.is_mm_file()

#refreshes the currently active file from the server
class SynchronizeActiveMetadataCommand(sublime_plugin.WindowCommand):
    def run(self):
        params = {
            "files"         : [util.get_active_file()]
        }
        mm.call('synchronize', context=self, params=params)
        util.send_usage_statistics('Synchronized Active File to Server')

    def is_visible(self):
        return util.is_mm_file()


#opens the apex class, trigger, component or page on the server
class SynchronizeSelectedMetadataCommand(sublime_plugin.WindowCommand):
    def run (self, dirs, files):
        if dirs != None and type(dirs) is list and len(dirs) > 0:
            params = {
                "directories"   : dirs
            }
        elif files != None and type(files) is list and len(files) > 0:
            params = {
                "files"         : files
            }
        mm.call('synchronize', context=self, params=params)
        util.send_usage_statistics('Synchronized Selected Metadata With Server')

    def is_visible(self, dirs, files):
        if dirs != None and type(dirs) is list and len(dirs) > 0:
            for d in dirs:
                if util.is_config.mm_dir(d):
                    return True
        if files != None and type(files) is list and len(files) > 0:
            for f in files:
                if util.util.is_mm_file(f):
                    return True
        return False

#opens the apex class, trigger, component or page on the server
class RunActiveApexTestsCommand(sublime_plugin.WindowCommand):
    def run(self):
        filename, ext = os.path.splitext(os.path.basename(util.get_active_file()))
        params = {
            "selected"         : [filename]
        }
        mm.call('unit_test', context=self, params=params)
        util.send_usage_statistics('Run Apex Tests in Active File')

    def is_visible(self):
        return util.is_apex_class_file()

    def is_enabled(self):
        return util.is_apex_test_file()


#opens the apex class, trigger, component or page on the server
class RunSelectedApexTestsCommand(sublime_plugin.WindowCommand):
    def run(self, files):
        if files != None and type(files) is list and len(files) > 0:
            params = {
                "selected"         : []
            }
            for f in files:
                filename, ext = os.path.splitext(os.path.basename(f))
                params['selected'].append(filename)

            mm.call('unit_test', context=self, params=params)
            util.send_usage_statistics('Run Apex Tests in Active File')

    def is_visible(self, files):
        if files != None and type(files) is list and len(files) > 0:
            for f in files:
                if util.is_apex_class_file(f): 
                    return True
        return False
        
    def is_enabled(self, files):
        if files != None and type(files) is list and len(files) > 0:
            for f in files:
                if util.is_apex_test_file(f): return True
        return False

#opens the apex class, trigger, component or page on the server
class OpenActiveSfdcUrlCommand(sublime_plugin.WindowCommand):
    def run(self):
        params = {
            "files"         : [util.get_active_file()]
        }
        mm.call('open_sfdc_url', context=self, params=params)
        util.send_usage_statistics('Open Active File On Server')

    def is_visible(self):
        return util.is_mm_file()

    def is_enabled(self):
        return util.is_browsable_file()

#opens the WSDL file for apex webservice classes
class OpenActiveSfdcWsdlUrlCommand(sublime_plugin.WindowCommand):
    def run(self):
        params = {
            "files"         : [util.get_active_file()],
            "type"          : "wsdl"
        }
        mm.call('open_sfdc_url', context=self, params=params)
        util.send_usage_statistics('Open Active WSDL File On Server')

    def is_visible(self):
        return util.is_apex_class_file()

    def is_enabled(self):
        if util.is_apex_webservice_file(): 
            return True
        return False

#opens the apex class, trigger, component or page on the server
class OpenSelectedSfdcUrlCommand(sublime_plugin.WindowCommand):
    def run (self, files):
        if files != None and type(files) is list and len(files) > 0:
            params = {
                "files"         : files
            }
        mm.call('open_sfdc_url', context=self, params=params)
        util.send_usage_statistics('Open Selected File On Server')

    def is_visible(self, files):
        if not util.is_mm_project: return False
        if files != None and type(files) is list and len(files) > 0:
            for f in files:
                if util.is_browsable_file(f): return True
        return False

#opens the WSDL file for apex webservice classes
class OpenSelectedSfdcWsdlUrlCommand(sublime_plugin.WindowCommand):
    def run(self, files):
        if files != None and type(files) is list and len(files) > 0:
            params = {
                "files"         : files,
                "type"          : "wsdl"
            }
        mm.call('open_sfdc_url', context=self, params=params)
        util.send_usage_statistics('Open Selected WSDL File On Server')

    def is_visible(self, files):
        if files != None and type(files) is list and len(files) > 0:
            for f in files:
                if util.is_apex_class_file(f): 
                    return True
        return False
        
    def is_enabled(self, files):
        if files != None and type(files) is list and len(files) > 0:
            for f in files:
                if util.is_apex_webservice_file(f): 
                    return True
        return False

#deletes selected metadata
class DeleteMetadataCommand(sublime_plugin.WindowCommand):
    def run(self, files):
        if sublime.ok_cancel_dialog("Are you sure you want to delete the selected files from Salesforce?", "Delete"):
            params = {
                "files" : files
            }
            mm.call('delete', context=self, params=params)
            util.send_usage_statistics('Delete Metadata')

    def is_visible(self):
        return util.is_mm_file()

    def is_enabled(self):
        return util.is_mm_file()

#deletes selected metadata
class DeleteActiveMetadataCommand(sublime_plugin.WindowCommand):
    def run(self):
        active_path = util.get_active_file()
        active_file = os.path.basename(active_path)
        if sublime.ok_cancel_dialog("Are you sure you want to delete "+active_file+" file from Salesforce?", "Delete"):
            params = {
                "files" : [active_file]
            }
            result = mm.call('delete', context=self, params=params)
            self.window.run_command("close")
            util.send_usage_statistics('Delete Metadata')

    def is_enabled(self):
        return util.is_mm_file()

    def is_visible(self):
        return util.is_mm_project()

#attempts to compile the entire project
class CompileProjectCommand(sublime_plugin.WindowCommand):
    def run(self):
        if sublime.ok_cancel_dialog("Are you sure you want to compile the entire project?", "Compile Project"):
            mm.call('compile_project', context=self)
            util.send_usage_statistics('Compile Project')

    def is_enabled(command):
        return util.is_mm_project()

#refreshes the currently active file from the server
class IndexApexOverlaysCommand(sublime_plugin.WindowCommand):
    def run(self):
        mm.call('index_apex_overlays', False, context=self)
        util.send_usage_statistics('Index Apex Overlays')  

    def is_enabled(command):
        return util.is_mm_project()

#refreshes the currently active file from the server
class IndexApexFileProperties(sublime_plugin.WindowCommand):
    def run(self):
        mm.call('index_apex', False, context=self)
        util.send_usage_statistics('Index Apex File Properties')  

    def is_enabled(command):
        return util.is_mm_project()

#indexes the meta data based on packages.xml
class IndexMetadataCommand(sublime_plugin.WindowCommand):
    def run(self):
        mm.call('index_metadata', True, context=self)
        util.send_usage_statistics('Index Metadata')  

    def is_enabled(command):
        return util.is_mm_project()

#refreshes the currently active file from the server
class FetchLogsCommand(sublime_plugin.WindowCommand):
    def run(self):
        mm.call('fetch_logs', False)
        util.send_usage_statistics('Fetch Apex Logs')  

#when a class or trigger file is opened, adds execution overlay markers if applicable
class ExecutionOverlayLoader(sublime_plugin.EventListener):
    def on_load(self, view):
        print('attempting to load apex overlays for current file')
        try:
            fileName, ext = os.path.splitext(view.file_name())
            if ext == ".cls" or ext == ".trigger":
                api_name = fileName.split("/")[-1] 
                overlays = util.parse_json_from_file(util.mm_project_directory()+"/config/.overlays")
                lines = []
                for o in overlays:
                    if o['API_Name'] == api_name:
                        lines.append(int(o["Line"]))
                sublime.set_timeout(lambda: util.mark_overlays(lines), 100)
        except Exception as e:
            print('execution overlay loader error')

#deletes overlays
class DeleteOverlaysCommand(sublime_plugin.WindowCommand):
    def run(self):
        options = [['Delete All In This File', '*']]
        fileName, ext = os.path.splitext(util.get_active_file())
        if ext == ".cls" or ext == ".trigger":
            self.api_name = fileName.split("/")[-1] 
            overlays = util.get_execution_overlays(util.get_active_file())
            for o in overlays:
                options.append(['Line '+str(o["Line"]), str(o["Id"])])
        self.results = options
        self.window.show_quick_panel(options, self.panel_done, sublime.MONOSPACE_FONT)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        self.overlay = self.results[picked]
        params = {
            "id" : self.overlay[1]
        }
        mm.call('delete_apex_overlay', context=self, params=params)
        util.send_usage_statistics('New Apex Overlay') 

#creates a new overlay
class NewOverlayCommand(sublime_plugin.WindowCommand):
    def run(self):
        fileName, ext = os.path.splitext(util.get_active_file())
        if ext == ".cls" or ext == ".trigger":
            if ext == '.cls':
                self.object_type = 'ApexClass'
            else: 
                self.object_type = 'ApexTrigger'
            self.api_name = fileName.split("/")[-1] 
            number_of_lines = util.get_number_of_lines_in_file(util.get_active_file())
            lines = list(xrange(number_of_lines))
            options = []
            lines.pop(0)
            for l in lines:
                options.append(str(l))
            self.results = options
            self.window.show_quick_panel(options, self.panel_done, sublime.MONOSPACE_FONT)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        self.line_number = self.results[picked]
        #print self.line_number
        params = {
            "ActionScriptType"      : "None",
            "Object_Type"           : self.object_type,
            "API_Name"              : self.api_name,
            "IsDumpingHeap"         : True,
            "Iteration"             : 1,
            "Line"                  : int(self.line_number)
        }
        #util.mark_overlay(self.line_number) #cant do this here bc it removes the rest of them
        mm.call('new_apex_overlay', context=self, params=params)
        util.send_usage_statistics('New Apex Overlay')  

#right click context menu support for resource bundle creation
class NewResourceBundleCommand(sublime_plugin.WindowCommand):
    def run(self, files):
        if sublime.ok_cancel_dialog("Are you sure you want to create resource bundle(s) for the selected static resource(s)", "Create Resource Bundle(s)"):
            util.create_resource_bundle(self, files) 
            util.send_usage_statistics('New Resource Bundle (Sidebar)')
    def is_visible(self):
        return util.is_mm_project()

#creates a MavensMate project from an existing directory
class CreateMavensMateProject(sublime_plugin.WindowCommand):
    def run (self, dirs):
        directory = dirs[0]

        if directory.endswith("/src"):
            printer = PanelPrinter.get(self.window.id())
            printer.show()
            printer.write('\n[OPERATION FAILED] You must run this command from the project folder, not the "src" folder\n')
            return            
 
        dir_entries = os.listdir(directory)
        has_source_directory = False
        for entry in dir_entries:
            if entry == "src":
                has_source_directory = True
                break

        if has_source_directory == False:
            printer = PanelPrinter.get(self.window.id())
            printer.show()
            printer.write('\n[OPERATION FAILED] Unable to locate "src" folder\n')
            return
        
        dir_entries = os.listdir(directory+"/src")
        has_package = False
        for entry in dir_entries:
            if entry == "package.xml":
                has_package = True
                break

        if has_package == False:
            printer = PanelPrinter.get(self.window.id())
            printer.show()
            printer.write('\n[OPERATION FAILED] Unable to locate package.xml in src folder \n')
            return        

        params = {
            "directory" : directory
        }
        mm.call('new_project_from_existing_directory', params=params)
        util.send_usage_statistics('New Project From Existing Directory')  

    def is_visible(self):
        return not util.is_mm_project()

#generic handler for writing text to an output panel (sublime text 3 requirement)
class MavensMateOutputText(sublime_plugin.TextCommand):
    def run(self, edit, text, *args, **kwargs):
        size = self.view.size()
        self.view.set_read_only(False)
        self.view.insert(edit, size, text)
        self.view.set_read_only(True)
        self.view.show(size)

    def is_visible(self):
        return False

    def is_enabled(self):
        return True

    def description(self):
        return

class WriteOperationStatus(sublime_plugin.TextCommand):
    def run(self, edit, text, *args, **kwargs):
        kw_region = kwargs.get('region', [0,0])
        status_region = sublime.Region(kw_region[0],kw_region[1])
        #print(status_region)
        size = self.view.size()
        self.view.set_read_only(False)
        self.view.replace(edit, status_region, text)
        self.view.set_read_only(True)
        #self.view.show(size)

    def is_visible(self):
        return False

    def is_enabled(self):
        return True

    def description(self):
        return

class CancelCurrentCommand(sublime_plugin.WindowCommand):
    
    def run(self):
        current_thread = ThreadTracker.get_current(self.window.id())
        if current_thread:
            current_thread.kill()

    #def is_visible(self, paths = None):
    #    return ThreadTracker.get_current(self.window.id()) != None

####### <--START--> COMMANDS THAT ARE NOT *OFFICIALLY* SUPPORTED IN 2.0 BETA ##########

#updates MavensMate plugin
class UpdateMeCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        sublime.message_dialog("Use the \"Plugins\" option in MavensMate.app to update MavensMate for Sublime Text.")

#opens the MavensMate shell
class NewShellCommand(sublime_plugin.TextCommand):
    def run(self, edit): 
        util.send_usage_statistics('New Shell Command')
        sublime.active_window().show_input_panel("MavensMate Command", "", self.on_input, None, None)
    
    def on_input(self, input): 
        try:
            ps = input.split(" ")
            if ps[0] == 'new':
                metadata_type, metadata_name, object_name = '', '', ''
                metadata_type   = ps[1]
                proper_type     = command_helper.dict[metadata_type][0]
                metadata_name   = ps[2]
                if len(ps) > 3:
                    object_name = ps[3]
                options = {
                    'metadata_type'     : proper_type,
                    'metadata_name'     : metadata_name,
                    'object_api_name'   : object_name,
                    'apex_class_type'   : 'Base'
                }
                mm.call('new_metadata', params=options)
            elif ps[0] == 'bundle' or ps[0] == 'b':
                deploy_resource_bundle(ps[1])
            else:
                util.print_debug_panel_message('Unrecognized command: ' + input + '\n')
        except:
            util.print_debug_panel_message('Unrecognized command: ' + input + '\n')

#completions for force.com-specific use cases
class ApexCompletions(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        settings = sublime.load_settings('mavensmate.sublime-settings')
        if settings.get('mm_autocomplete') == False or util.is_mm_project() == False:
            return []

        pt = locations[0] - len(prefix) - 1
        ch = view.substr(sublime.Region(pt, pt + 1))
        if not ch == '.': return []

        word = view.substr(view.word(pt))

        fn, ext = os.path.splitext(view.file_name())
        
        if ext != '.cls' and ext != '.trigger' and (word == None or word == ''):
            return []

        ##OK START COMPLETIONS

        _completions = []
        lower_prefix = word.lower()
        print(word)
        #print(lower_prefix)

        if lower_prefix == 'this':
            full_file_path = os.path.splitext(util.get_active_file())[0]
            base = os.path.basename(full_file_path)
            file_name = os.path.splitext(base)[0]            
            _completions = util.get_apex_completions(file_name) 
            return sorted(_completions)

        ## HANDLE APEX STATIC METHODS
        ## String.valueOf, Double.toString(), etc.
        elif os.path.isfile(config.mm_dir+"/support/lib/apex/"+lower_prefix+".json"): 
            prefix = prefix.lower()
            json_data = open(config.mm_dir+"/support/lib/apex/"+lower_prefix+".json")
            data = json.load(json_data)
            json_data.close()
            pd = data["static_methods"]
            for method in pd:
                _completions.append((method, method))
            return sorted(_completions)
        
        ## HANDLE CUSTOM APEX CLASS STATIC METHODS 
        ## MyCustomClass.some_static_method
        elif os.path.isfile(util.mm_project_directory()+"/src/classes/"+word+".cls"):
            _completions = util.get_apex_completions(word) 
            return sorted(_completions)  

        ## HANDLE CUSTOM APEX INSTANCE METHOD ## 
        ## MyClass mc = new MyClass()
        ## mc.??
        else: 
            #self.process = subprocess.Popen("{0} {1}".format(self.mm_location, self.get_arguments()), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            object_name = None
            object_name_lower = None
            variables = util.get_variable_list(view)

            print(variables)

            for v in variables['result']:
                #print(v)
                if 'variableName' in v and v['variableName'].lower() == word.lower():
                    object_name = v['type']
                    if '.' in object_name:
                        object_name = object_name.split('.')[-1]
                    object_name_lower = object_name.lower()
                    break

            print('object_name: ', object_name)
            print(os.path.isfile(util.mm_project_directory()+"/config/.org_metadata"))

            if object_name != None:
                if os.path.isfile(config.mm_dir+"/support/lib/apex/"+object_name_lower+".json"): #=> apex instance methods
                    json_data = open(config.mm_dir+"/support/lib/apex/"+object_name_lower+".json")
                    data = json.load(json_data)
                    json_data.close()
                    pd = data["instance_methods"]
                    for method in pd:
                        _completions.append((method, method))
                    return sorted(_completions)
                elif os.path.isfile(util.mm_project_directory()+"/config/.org_metadata"): #=> parse org metadata
                    jsonData = util.parse_json_from_file(util.mm_project_directory()+"/config/.org_metadata")
                    for metadata_type in jsonData:
                        if 'xmlName' in metadata_type and metadata_type['xmlName'] == 'CustomObject':
                            for object_type in metadata_type['children']:
                                if 'text' in object_type and object_type['text'].lower() == object_name_lower:
                                    for attr in object_type['children']:
                                        if 'text' in attr and attr['text'] == 'fields':
                                            for field in attr['children']:
                                                _completions.append((field['text'], field['text']))
                    return sorted(_completions)
                elif os.path.isfile(util.mm_project_directory()+"/config/objects/"+object_name_lower+".object"): #=> object fields
                    object_dom = parse(util.mm_project_directory()+"/config/objects/"+object_name_lower+".object")
                    for node in object_dom.getElementsByTagName('fields'):
                        field_name = ''
                        field_type = ''
                        for child in node.childNodes:                            
                            if child.nodeName != 'fullName' and child.nodeName != 'type': continue
                            if child.nodeName == 'fullName':
                                field_name = child.firstChild.nodeValue
                            elif child.nodeName == 'type':
                                field_type = child.firstChild.nodeValue
                        _completions.append((field_name+" \t"+field_type, field_name))
                    return sorted(_completions)
                elif os.path.isfile(util.mm_project_directory()+"/src/objects/"+object_name_lower+".object"): #=> object fields
                    object_dom = parse(util.mm_project_directory()+"/src/objects/"+object_name_lower+".object")
                    for node in object_dom.getElementsByTagName('fields'):
                        field_name = ''
                        field_type = ''
                        for child in node.childNodes:                            
                            if child.nodeName != 'fullName' and child.nodeName != 'type': continue
                            if child.nodeName == 'fullName':
                                field_name = child.firstChild.nodeValue
                            elif child.nodeName == 'type':
                                field_type = child.firstChild.nodeValue
                        _completions.append((field_name+" \t"+field_type, field_name))
                    return sorted(_completions)
                
                elif os.path.isfile(util.mm_project_directory()+"/src/classes/"+object_name_lower+".cls"): #=> apex classes
                    search_name = util.prep_for_search(object_name)
                    _completions = util.get_apex_completions(search_name)
                    return sorted(_completions)

    def show_completions(self, view, completions):
        if completions:
            self.completions = completions
            view.run_command("hide_auto_complete")
            sublime.set_timeout(functools.partial(self.show, view), 0)

    def show(self, view):
        view.run_command("auto_complete", {
            'disable_auto_insert': True,
            'api_completions_only': True,
            'next_completion_if_showing': False,
            'auto_complete_commit_on_tab': True,
        })


class Autocomplete(sublime_plugin.EventListener):
    """
    Sublime Text autocompletion integration
    """

    completions = []
    cplns_ready = None

    def on_query_completions(self, view, prefix, locations):
        """ Sublime autocomplete event handler

            Get completions depends on current cursor position and return
            them as list of ('possible completion', 'completion type')

            :param view: `sublime.View` object
            :type view: sublime.View
            :param prefix: string for completions
            :type prefix: basestring
            :param locations: offset from beginning
            :type locations: int

            :return: list
        """
        if self.cplns_ready:
            self.cplns_ready = None
            if self.completions:
                cplns, self.completions = self.completions, []
                return [tuple(i) for i in cplns]
            return

        # nothing to do with non-python code
        if not util.is_mm_project():
            return

        # get completions list
        if self.cplns_ready is None:
            ask_daemon(view, self.show_completions, 'autocomplete', locations[0])
            self.cplns_ready = False
        return

    def show_completions(self, view, completions):
        # XXX check position
        self.cplns_ready = True
        if completions:
            self.completions = completions
            view.run_command("hide_auto_complete")
            sublime.set_timeout(functools.partial(self.show, view), 0)

    def show(self, view):
        view.run_command("auto_complete", {
            'disable_auto_insert': True,
            'api_completions_only': True,
            'next_completion_if_showing': False,
            'auto_complete_commit_on_tab': True,
        })

#prompts users to select a static resource to create a resource bundle
class CreateResourceBundleCommand(sublime_plugin.WindowCommand):
    def run(self):
        srs = []
        for dirname in os.listdir(util.mm_project_directory()+"/src/staticresources"):
            if dirname == '.DS_Store' or dirname == '.' or dirname == '..' or '-meta.xml' in dirname : continue
            srs.append(dirname)
        self.results = srs
        self.window.show_quick_panel(srs, self.panel_done,
            sublime.MONOSPACE_FONT)
    def is_visible(self):
        return util.is_mm_project()

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        ps = []
        ps.append(util.mm_project_directory()+"/src/staticresources/"+self.results[picked])
        util.create_resource_bundle(self, ps)
        
#deploys selected resource bundle to the server
class DeployResourceBundleCommand(sublime_plugin.WindowCommand):
    def run(self):
        self.rbs_map = {}
        rbs = []
        for dirname in os.listdir(util.mm_project_directory()+"/resource-bundles"):
            if dirname == '.DS_Store' or dirname == '.' or dirname == '..' : continue
            rbs.append(dirname)
        self.results = rbs
        self.window.show_quick_panel(rbs, self.panel_done,
            sublime.MONOSPACE_FONT)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        deploy_resource_bundle(self.results[picked])

def deploy_resource_bundle(bundle_name):
    if '.resource' not in bundle_name:
        bundle_name = bundle_name + '.resource'
    printer = PanelPrinter.get(sublime.active_window().id())
    printer.show()
    printer.write('\nBundling and deploying to server => ' + bundle_name + '\n') 
    # delete existing sr
    if os.path.exists(util.mm_project_directory()+"/src/staticresources/"+bundle_name):
        os.remove(util.mm_project_directory()+"/src/staticresources/"+bundle_name)
    # zip bundle to static resource dir 
    os.chdir(util.mm_project_directory()+"/resource-bundles/"+bundle_name)
    cmd = "zip -r -X '"+util.mm_project_directory()+"/src/staticresources/"+bundle_name+"' *"      
    os.system(cmd)
    #compile
    file_path = util.mm_project_directory()+"/src/staticresources/"+bundle_name
    params = {
        "files" : [file_path]
    }
    mm.call('compile', params=params)
    util.send_usage_statistics('Deploy Resource Bundle')


#TODO: this is not longer OK in ST3 from what i understand
#util.package_check()
#util.start_mavensmate_app()  
#util.check_for_updates()
#util.send_usage_statistics('Startup')
