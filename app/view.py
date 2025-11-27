import os
from django.http import JsonResponse
import re


def get_last_commit(request):
    try:
        # Получаем хэш коммита из Railway
        git_hash = os.environ.get('RAILWAY_GIT_COMMIT_SHA', 'unknown')

        # Получаем сообщение коммита из Railway
        git_message = os.environ.get('RAILWAY_GIT_COMMIT_MESSAGE', 'unknown')

        re_version = re.search(r'(?:[vV]\.)?(\d+\.\d+\.\d+)', git_message)

        return JsonResponse({
            'status': 'ok',
            'hash': git_hash,
            'version': re_version.group(1),
            'commit_message': git_message
        })
    except Exception as e:
        return JsonResponse({
            'status': 'no',
            'error': str(e)
        })
