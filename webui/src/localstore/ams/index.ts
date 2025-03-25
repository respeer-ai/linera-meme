import { defineStore } from 'pinia'
import { Application, GetApplicationsRequest, StoreType } from './types'
import { ApolloClient } from '@apollo/client/core'
import { getClientOptions } from 'src/apollo'
import { provideApolloClient, useQuery } from '@vue/apollo-composable'
import { APPLICATIONS } from 'src/graphql'
import { constants } from 'src/constant'
import { graphqlResult } from 'src/utils'

const options = /* await */ getClientOptions()
const apolloClient = new ApolloClient(options)

export const useAmsStore = defineStore('ams', {
  state: () => ({
    applications: [] as Array<Application>
  }),
  actions: {
    getApplications(req: GetApplicationsRequest, done?: (error: boolean, rows?: Application[]) => void) {
      const { /* result, refetch, fetchMore, */ onResult, onError } = provideApolloClient(apolloClient)(() => useQuery(APPLICATIONS, {
        createdAfter: req.createdAfter,
        limit: req.limit,
        endpoint: 'ams'
      }, {
        fetchPolicy: 'network-only'
      }))

      onResult((res) => {
        const applications = graphqlResult.data(res, 'applications') as Application[]
        this.appendApplications(applications)
        done?.(false, applications)
      })

      onError(() => {
        done?.(true)
      })
    },
    appendApplications(applications: Application[]) {
      applications.forEach((application) => {
        const index = this.applications.findIndex((el) => el.applicationId === application.applicationId)
        this.applications.splice(index >= 0 ? index : 0, index >= 0 ? 1 : 0, application)
      })
    }
  },
  getters: {
    applicationLogo (): (application: Application) => string {
      return (application: Application) => {
        switch (application.logoStoreType) {
          case StoreType.Blob:
          case StoreType.S3:
            return constants.APPLICATION_URLS.BLOB_GATEWAY + '/images/' + application.logo
          case StoreType.Ipfs:
            return application.logo
        }
      }
    }
  }
})

export * from './types'
