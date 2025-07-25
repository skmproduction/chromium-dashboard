# Copyright 2023 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import logging
from google.cloud import ndb

from api.converters import stage_to_json_dict
from internals.core_enums import (
    OT_EXTENSION_STAGE_TYPES,
    OT_READY_FOR_CREATION,
    OT_CREATED,
    OT_CREATION_FAILED,
    OT_ACTIVATION_FAILED)
from internals.core_models import Stage
from internals.review_models import Gate, Vote

from framework import basehandlers
from framework import permissions


class OriginTrialsRequests(basehandlers.FlaskHandler):
  """Display any origin trials requests."""

  TEMPLATE_PATH = 'admin/features/ot_requests.html'

  @permissions.require_admin_site
  def get_template_data(self, **kwargs):
    stages_with_requests = Stage.query(
        ndb.OR(Stage.ot_action_requested == True,
               Stage.ot_setup_status == OT_READY_FOR_CREATION)).fetch()
    stages_with_failures = Stage.query(
        ndb.OR(Stage.ot_setup_status == OT_ACTIVATION_FAILED,
               Stage.ot_setup_status == OT_CREATION_FAILED)).fetch()
    stages_awaiting_activation = Stage.query(
        Stage.ot_setup_status == OT_CREATED).fetch()
    creation_stages = []
    extension_stages = []
    for stage in stages_with_requests:
      stage_dict = stage_to_json_dict(stage)
      # Group up creation and extension requests.
      if stage_dict['stage_type'] in OT_EXTENSION_STAGE_TYPES:
        gate: Gate = Gate.query(Gate.stage_id == stage_dict['id']).get()
        if gate and gate.state in (Vote.NA, Vote.APPROVED):
          # Information will be needed from the original OT stage.
          ot_stage = Stage.get_by_id(stage_dict['ot_stage_id'])
          if ot_stage is None:
            logging.warning(
              f'Extension stage {stage_dict["id"]} '
              f'found with invalid OT stage ID {stage_dict["ot_stage_id"]}.')
            continue
          ot_stage_dict = stage_to_json_dict(ot_stage)
          # Supply both the OT stage and the extension stage.
          extension_stages.append({
              'ot_stage': ot_stage_dict,
              'extension_stage': stage_dict,
            })
      else:
        creation_stages.append(stage_dict)

    failed_stages = [stage_to_json_dict(s) for s in stages_with_failures]
    activation_pending_stages = [
        stage_to_json_dict(s) for s in stages_awaiting_activation]
    return {
        'creation_stages': creation_stages,
        'extension_stages': extension_stages,
        'activation_pending_stages': activation_pending_stages,
        'failed_stages': failed_stages,
      }
