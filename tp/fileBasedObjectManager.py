# Trajectory Prediction application
# CLASS Project: https://class-project.eu/
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     https://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# Created on 8 Jun 2020
# @author: Jorge Montero - ATOS
#

import os
import json

class FileBasedObjectManager:

    vehicles = {}
    results = {}
    output_path = ""
    file_content = ""
    raw_output = ""
    visual_output = ""

    def __init__(self, path='.', filename="worflow.log"):

        self.output_path = path

        # read workflow test data
        infile = path + "/" + filename

        content = str()
        with open(infile) as f:
            content = f.read().splitlines()
            self.file_content = content

    def getFileContent(self):
        return self.file_content
    
    def getVehiclesIDs(self):
        return self.vehicles.keys()

    def getVehicleByID(self, v_id):
        return self.vehicles[v_id]
    
    def storeVehicle(self, v_id, v):
        self.vehicles[v_id] = v

    def getUpdatedObject(self, oid):
        return oid, self.getVehicleByID(oid)

    def storeResult(self, frame, v_id, v_type, fx, fy, ft):
        local_result = {}
        local_result["v_id"] = v_id
        local_result["v_type"] = v_type
        local_result["x"] = fx
        local_result["y"] = fy
        local_result["t"] = ft
                
        if frame in self.results.keys():
            a = self.results[frame]
            a.append(local_result)
            self.results[frame] = a
        else:
            self.results[frame] = [local_result] 

    def getResult(self):
        return self.results

    def storeRawResult(self, raw_out):
        self.raw_output = self.raw_output + raw_out + "\n"

    def storeVisualResult(self, visual_out):
        self.visual_output = self.visual_output + visual_out + "\n"
        
    def createResultsFile(self):
        with open(self.output_path + "/results.txt", 'w') as outfile:
            json.dump(self.results, outfile)
        with open(self.output_path + "/raw_results_TP.txt", "w") as raw_file:
            raw_file.write(self.raw_output)
        with open(self.output_path + "/visual_results_TP.txt", "w") as visual_file:
            visual_file.write(self.visual_output)
        
        
