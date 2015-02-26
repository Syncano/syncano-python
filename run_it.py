import syncano

connection = syncano.connect(api_key='fec060a02b83a0ca18fef98472396951a0fd847e')
instance = connection.instances[0]
cls = instance.classes[0]
objects = cls.objects
print objects[0]
