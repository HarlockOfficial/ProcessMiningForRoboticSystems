import os

import requests as requests

import testPM4PY


def download_file_content(url):
    base_url = 'https://bitbucket.org/proslabteam/colliery_validation/raw/74d06e1b38f9f8941a3e5ca24617f5ba5dd95e7e/'
    response = requests.get(base_url + url)
    if response.status_code != 200:
        print(response.status_code, response.reason)
        raise Exception('Failed to download file')
    return response.content


def create_path(path):
    import os
    os.makedirs(os.path.dirname('./' + path), exist_ok=True)
    with open('./' + path, 'w') as f:
        pass


def main(download_tests=True, run_tests=True):
    test_file_list = [
        ('artificial2/PartyA.xes', 'generated/2/party_a.xes'),
        ('artificial2/PartyB.xes', 'generated/2/party_b.xes'),
        ('artificial2/model.bpmn', 'generated/2/final.bpmn'),
        ('artificial3/PartyA.xes', 'generated/3/party_a.xes'),
        ('artificial3/PartyB.xes', 'generated/3/Party_b.xes'),
        ('artificial3/PartyC.xes', 'generated/3/party_c.xes'),
        ('artificial3/model.bpmn', 'generated/3/final.bpmn'),
        ('artificial4/PartyA.xes', 'generated/4/party_a.xes'),
        ('artificial4/PartyC.xes', 'generated/4/party_c.xes'),
        ('artificial4/model.bpmn', 'generated/4/final.bpmn'),
        ('artificial5/PartyA.xes', 'generated/5/party_a.xes'),
        ('artificial5/PartyB.xes', 'generated/5/party_b.xes'),
        ('artificial5/PartyC.xes', 'generated/5/party_c.xes'),
        ('artificial5/PartyD.xes', 'generated/5/party_d.xes'),
        ('artificial5/model.bpmn', 'generated/5/final.bpmn'),
        ('helathcare/Hospital.xes', 'healthcare/hospital.xes'),
        ('helathcare/Gynecologist.xes', 'healthcare/gynecologist.xes'),
        ('helathcare/Laboratory.xes', 'healthcare/laboratory.xes'),
        ('helathcare/Patient.xes', 'healthcare/patient.xes'),
        ('helathcare/model.bpmn', 'healthcare/final.bpmn'),
        ('real1/DINGO.xes', 'real/1/dingo.xes'),
        ('real1/REX.xes', 'real/1/rez.xes'),
        ('real1/collaboration_discovered_inductive.bpmn', 'real/1/final.bpmn'),
        ('real2/Customer.xes', 'real/2/customer.xes'),
        ('real2/TravelAgency.xes', 'real/2/travel_agency.xes'),
        ('real2/collaboration_discovered_inductive.bpmn', 'real/2/final.bpmn'),
        ('real3/Controller.xes', 'real/3/controller.xes'),
        ('real3/Thermostat.xes', 'real/3/thermostat.xes'),
        ('real3/User.xes', 'real/3/user.xes'),
        ('real3/collaboration_discovered_inductive.bpmn', 'real/3/final.bpmn'),
        ('real4/Bank.xes', 'real/4/bank.xes'),
        ('real4/Visitor.xes', 'real/4/visitor.xes'),
        ('real4/Zoo.xes', 'real/4/zoo.xes'),
        ('real4/collaboration_discovered_inductive.bpmn', 'real/4/final.bpmn'),
        ('smartagriculture/drone.xes', 'smart_agriculture/drone.xes'),
        ('smartagriculture/tractor_1.xes', 'smart_agriculture/tractor_1.xes'),
        ('smartagriculture/tractor_2.xes', 'smart_agriculture/tractor_2.xes'),
        ('smartagriculture/collaboration_discovered_inductive.bpmn', 'smart_agriculture/final.bpmn'),
    ]
    if download_tests:
        for url, path in test_file_list:
            print('Downloading {} to {}'.format(url, path))
            file_content = download_file_content(url)
            create_path(path)
            with open(path, 'wb') as f:
                f.write(file_content)
    if run_tests:
        for dirname, dirnames, filenames in os.walk('.'):
            if len(dirnames) == 0 and len(filenames) > 0:
                print('Running tests for {}'.format(os.path.join(dirname)))
                xes_files = [os.path.join(dirname, f) for f in filenames if f.endswith('.xes')]
                process_names = [os.path.splitext(f)[0] for f in filenames if f.endswith('.xes')]
                testPM4PY.import_xes(xes_files, process_names, os.path.join(dirname, 'test.ptml'), os.path.join(dirname, 'test.bpmn'))


if __name__ == "__main__":
    main(download_tests=False, run_tests=True)
